package ws

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"sync"

	"github.com/golang-jwt/jwt/v5"
	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  4096,
	WriteBufferSize: 4096,
	CheckOrigin: func(r *http.Request) bool {
		// Allow all origins (mobile apps, web portals)
		return true
	},
}

// RoomMessage represents a message destined for a specific room.
type RoomMessage struct {
	Room     string          `json:"room"`
	Type     string          `json:"type"`
	Data     json.RawMessage `json:"data"`
	SenderID string          `json:"sender_id,omitempty"`
}

// Client represents a connected WebSocket client.
type Client struct {
	hub      *Hub
	conn     *websocket.Conn
	send     chan []byte
	rooms    map[string]bool
	userID   string
	userRole string
	mu       sync.Mutex
}

// Hub manages connected clients, rooms, and message broadcasting.
type Hub struct {
	clients    map[*Client]bool
	rooms      map[string]map[*Client]bool
	register   chan *Client
	unregister chan *Client
	broadcast  chan RoomMessage
	mu         sync.RWMutex
	rdb        *redis.Client
	secretKey  string
	logger     *slog.Logger
}

// NewHub creates a new Hub instance.
func NewHub(rdb *redis.Client, secretKey string, logger *slog.Logger) *Hub {
	if secretKey == "" {
		secretKey = "flexy-secret-key-fallback"
	}
	return &Hub{
		clients:    make(map[*Client]bool),
		rooms:      make(map[string]map[*Client]bool),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		broadcast:  make(chan RoomMessage, 1024),
		rdb:        rdb,
		secretKey:  secretKey,
		logger:     logger,
	}
}

// Run starts the Hub event loop.
func (h *Hub) Run(ctx context.Context) {
	// Start background Redis subscriber for inter-process/Django event broadcasts
	if h.rdb != nil {
		go h.subscribeRedis(ctx)
	}

	for {
		select {
		case <-ctx.Done():
			h.logger.Info("ws hub shutting down")
			h.mu.Lock()
			for client := range h.clients {
				close(client.send)
				_ = client.conn.Close()
				delete(h.clients, client)
			}
			h.mu.Unlock()
			return

		case client := <-h.register:
			h.mu.Lock()
			h.clients[client] = true
			h.mu.Unlock()

		case client := <-h.unregister:
			h.mu.Lock()
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.send)
				for room := range client.rooms {
					if members, exists := h.rooms[room]; exists {
						delete(members, client)
						if len(members) == 0 {
							delete(h.rooms, room)
						}
					}
				}
			}
			h.mu.Unlock()

		case msg := <-h.broadcast:
			h.dispatchMessage(msg)
		}
	}
}

// JoinRoom adds a client to a room.
func (h *Hub) JoinRoom(room string, client *Client) {
	h.mu.Lock()
	defer h.mu.Unlock()

	client.mu.Lock()
	client.rooms[room] = true
	client.mu.Unlock()

	if _, ok := h.rooms[room]; !ok {
		h.rooms[room] = make(map[*Client]bool)
	}
	h.rooms[room][client] = true
}

// LeaveRoom removes a client from a room.
func (h *Hub) LeaveRoom(room string, client *Client) {
	h.mu.Lock()
	defer h.mu.Unlock()

	client.mu.Lock()
	delete(client.rooms, room)
	client.mu.Unlock()

	if members, ok := h.rooms[room]; ok {
		delete(members, client)
		if len(members) == 0 {
			delete(h.rooms, room)
		}
	}
}

// BroadcastToRoom dispatches a message to all clients in a room.
func (h *Hub) BroadcastToRoom(room, eventType string, data []byte, senderID string) {
	h.broadcast <- RoomMessage{
		Room:     room,
		Type:     eventType,
		Data:     data,
		SenderID: senderID,
	}
}

func (h *Hub) dispatchMessage(msg RoomMessage) {
	h.mu.RLock()
	members, ok := h.rooms[msg.Room]
	if !ok || len(members) == 0 {
		h.mu.RUnlock()
		return
	}

	payload, err := json.Marshal(map[string]interface{}{
		"type": msg.Type,
		"data": json.RawMessage(msg.Data),
	})
	if err != nil {
		h.mu.RUnlock()
		return
	}

	// Copy member slice to release read lock quickly
	targets := make([]*Client, 0, len(members))
	for c := range members {
		// Prevent echo except for chat where sender needs real ID ACK
		if msg.SenderID != "" && c.userID == msg.SenderID && msg.Type != "chat" {
			continue
		}
		targets = append(targets, c)
	}
	h.mu.RUnlock()

	for _, client := range targets {
		select {
		case client.send <- payload:
		default:
			h.logger.Warn("client send channel full, closing", "user_id", client.userID)
			h.mu.Lock()
			delete(h.clients, client)
			close(client.send)
			h.mu.Unlock()
		}
	}
}

// subscribeRedis listens for events published to Redis by Django or other workers.
func (h *Hub) subscribeRedis(ctx context.Context) {
	pubsub := h.rdb.Subscribe(ctx, "engine:ws:broadcast")
	defer pubsub.Close()

	ch := pubsub.Channel()
	for {
		select {
		case <-ctx.Done():
			return
		case msg, ok := <-ch:
			if !ok {
				return
			}
			var rm RoomMessage
			if err := json.Unmarshal([]byte(msg.Payload), &rm); err == nil {
				h.broadcast <- rm
			} else {
				h.logger.Error("failed to decode redis ws broadcast", "err", err)
			}
		}
	}
}

// AuthenticateToken validates an HS256 JWT token and returns the user ID.
func (h *Hub) AuthenticateToken(tokenStr string) (string, error) {
	if tokenStr == "" {
		return "", nil
	}

	token, err := jwt.Parse(tokenStr, func(t *jwt.Token) (interface{}, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, jwt.ErrSignatureInvalid
		}
		return []byte(h.secretKey), nil
	})
	if err != nil || !token.Valid {
		// If custom or development mode with no secret match, return token as raw ID if UUID
		return "", err
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return "", jwt.ErrInvalidKeyType
	}

	if userID, ok := claims["user_id"]; ok && userID != nil {
		return fmt.Sprintf("%v", userID), nil
	}
	if sub, ok := claims["sub"]; ok {
		if s, ok := sub.(string); ok {
			return s, nil
		}
	}

	return "", nil
}

// ExtractToken retrieves the JWT token from query params or Authorization header.
func ExtractToken(r *http.Request) string {
	if token := r.URL.Query().Get("token"); token != "" {
		return token
	}
	auth := r.Header.Get("Authorization")
	if strings.HasPrefix(auth, "Bearer ") {
		return strings.TrimPrefix(auth, "Bearer ")
	}
	return ""
}
