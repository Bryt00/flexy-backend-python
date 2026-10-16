package ws

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
)

const (
	writeWait      = 10 * time.Second
	pongWait       = 60 * time.Second
	pingPeriod     = (pongWait * 9) / 10
	maxMessageSize = 65536
)

// InboundMessage represents a client-sent WebSocket frame.
type InboundMessage struct {
	Type string          `json:"type"`
	Data json.RawMessage `json:"data"`
}

// LocationPayload represents incoming driver location telemetry.
type LocationPayload struct {
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
	Heading   float64 `json:"heading"`
	Speed     float64 `json:"speed"`
}

// ReadPump listens for messages from the WebSocket connection.
func (c *Client) ReadPump() {
	defer func() {
		c.hub.unregister <- c
		_ = c.conn.Close()
	}()

	c.conn.SetReadLimit(maxMessageSize)
	_ = c.conn.SetReadDeadline(time.Now().Add(pongWait))
	c.conn.SetPongHandler(func(string) error {
		_ = c.conn.SetReadDeadline(time.Now().Add(pongWait))
		return nil
	})

	for {
		_, message, err := c.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				c.hub.logger.Debug("ws read error", "err", err, "user_id", c.userID)
			}
			break
		}

		c.handleIncoming(message)
	}
}

// WritePump pumps messages from the hub to the WebSocket connection.
func (c *Client) WritePump() {
	ticker := time.NewTicker(pingPeriod)
	defer func() {
		ticker.Stop()
		_ = c.conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.send:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if !ok {
				_ = c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			w, err := c.conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}
			_, _ = w.Write(message)

			// Drain queued messages into the same frame
			n := len(c.send)
			for i := 0; i < n; i++ {
				_, _ = w.Write([]byte{'\n'})
				_, _ = w.Write(<-c.send)
			}

			if err := w.Close(); err != nil {
				return
			}

		case <-ticker.C:
			_ = c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

// handleIncoming parses and processes client messages.
func (c *Client) handleIncoming(raw []byte) {
	var in InboundMessage
	if err := json.Unmarshal(raw, &in); err != nil {
		c.hub.logger.Debug("malformed inbound ws message", "raw", string(raw))
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	switch in.Type {
	case "location_update":
		var loc LocationPayload
		if err := json.Unmarshal(in.Data, &loc); err == nil && c.userID != "" {
			// 1. Update Redis GEO spatial index for driver location
			if c.hub.rdb != nil {
				c.hub.rdb.GeoAdd(ctx, "driver_locations", &redis.GeoLocation{
					Name:      c.userID,
					Longitude: loc.Longitude,
					Latitude:  loc.Latitude,
				})

				// Record coordinates in telemetry queue for Celery DB flush
				updateJSON, _ := json.Marshal(map[string]interface{}{
					"driver_id": c.userID,
					"latitude":  loc.Latitude,
					"longitude": loc.Longitude,
					"heading":   loc.Heading,
					"speed":     loc.Speed,
					"timestamp": time.Now().UTC().Format(time.RFC3339),
				})
				c.hub.rdb.LPush(ctx, "driver_location_updates_queue", updateJSON)
			}

			// 2. Broadcast to all rooms this driver is currently in (e.g. ride_{ride_id})
			c.mu.Lock()
			currentRooms := make([]string, 0, len(c.rooms))
			for r := range c.rooms {
				currentRooms = append(currentRooms, r)
			}
			c.mu.Unlock()

			for _, room := range currentRooms {
				c.hub.BroadcastToRoom(room, "driver_location", in.Data, c.userID)
			}

			// 3. Broadcast to global admin live map
			c.hub.BroadcastToRoom("global_rides", "driver_location", in.Data, c.userID)
		}

	case "chat":
		// Relay chat message immediately to counterparty in ride/delivery room
		c.mu.Lock()
		currentRooms := make([]string, 0, len(c.rooms))
		for r := range c.rooms {
			if strings.HasPrefix(r, "ride_") || strings.HasPrefix(r, "delivery_") || strings.HasPrefix(r, "chat_") {
				currentRooms = append(currentRooms, r)
			}
		}
		c.mu.Unlock()

		for _, room := range currentRooms {
			c.hub.BroadcastToRoom(room, "chat", in.Data, c.userID)
		}

		// Push to Redis for persistence into Django ChatMessage table
		if c.hub.rdb != nil {
			chatEnvelope, _ := json.Marshal(map[string]interface{}{
				"sender_id": c.userID,
				"payload":   json.RawMessage(in.Data),
				"timestamp": time.Now().UTC().Format(time.RFC3339),
			})
			c.hub.rdb.LPush(ctx, "chat_messages_queue", chatEnvelope)
		}

	case "ping":
		c.send <- []byte(`{"type":"pong"}`)
	}
}

// ServeWebSocket upgrades an HTTP connection and registers the client with specified initial rooms.
func ServeWebSocket(hub *Hub, w http.ResponseWriter, r *http.Request, initialRooms []string, role string) {
	tokenStr := ExtractToken(r)
	userID, err := hub.AuthenticateToken(tokenStr)
	if err != nil {
		hub.logger.Debug("ws auth warning", "err", err)
	}
	if userID == "" {
		// Fallback to query param or headers if supplied directly
		if uid := r.URL.Query().Get("user_id"); uid != "" {
			userID = uid
		}
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		hub.logger.Error("failed to upgrade websocket", "err", err)
		return
	}

	client := &Client{
		hub:      hub,
		conn:     conn,
		send:     make(chan []byte, 256),
		rooms:    make(map[string]bool),
		userID:   userID,
		userRole: role,
	}

	hub.register <- client

	// Join initial rooms
	for _, room := range initialRooms {
		if room != "" {
			hub.JoinRoom(room, client)
		}
	}

	// If driver, also join individual targeted dispatch room: driver_discovery_{userID}
	if userID != "" && (role == "driver" || role == "courier") {
		hub.JoinRoom(fmt.Sprintf("%s_discovery_%s", role, userID), client)
	}

	go client.WritePump()
	go client.ReadPump()
}

// ServeRideTrackingHandler handles /v1/rides/{ride_id}/track/{role}
func ServeRideTrackingHandler(hub *Hub, w http.ResponseWriter, r *http.Request, rideID, role string) {
	room := fmt.Sprintf("ride_%s", rideID)
	ServeWebSocket(hub, w, r, []string{room}, role)
}

// ServeDeliveryTrackingHandler handles /v1/deliveries/{delivery_id}/track/{role}
func ServeDeliveryTrackingHandler(hub *Hub, w http.ResponseWriter, r *http.Request, deliveryID, role string) {
	room := fmt.Sprintf("delivery_%s", deliveryID)
	ServeWebSocket(hub, w, r, []string{room}, role)
}

// ServeDiscoveryHandler handles /v1/rides/discovery and /v1/deliveries/discovery
func ServeDiscoveryHandler(hub *Hub, w http.ResponseWriter, r *http.Request, streamType string) {
	room := "discovery_rides"
	role := "driver"
	if streamType == "deliveries" {
		room = "discovery_deliveries"
		role = "courier"
	}
	ServeWebSocket(hub, w, r, []string{room}, role)
}

// ServeGlobalMapHandler handles /ws/rides/global/
func ServeGlobalMapHandler(hub *Hub, w http.ResponseWriter, r *http.Request) {
	ServeWebSocket(hub, w, r, []string{"global_rides"}, "admin")
}

// ServeAdminHeatmapHandler handles /v1/admin/tracking/ws/
func ServeAdminHeatmapHandler(hub *Hub, w http.ResponseWriter, r *http.Request) {
	ServeWebSocket(hub, w, r, []string{"admin_heatmap"}, "admin")
}

// ServeNotificationsHandler handles /v1/notifications/ws
func ServeNotificationsHandler(hub *Hub, w http.ResponseWriter, r *http.Request) {
	tokenStr := ExtractToken(r)
	userID, _ := hub.AuthenticateToken(tokenStr)
	room := ""
	if userID != "" {
		room = fmt.Sprintf("user_notifications_%s", userID)
	}
	ServeWebSocket(hub, w, r, []string{room}, "user")
}
