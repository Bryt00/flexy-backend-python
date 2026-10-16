package main

import (
	"context"
	"errors"
	"flag"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"flexy-engine/internal/api"
	"flexy-engine/internal/config"
	"flexy-engine/internal/heatmap"
	"flexy-engine/internal/location"
	"flexy-engine/internal/ws"

	"github.com/redis/go-redis/v9"
)

func main() {
	socketPath := flag.String("socket", os.Getenv("FLEXY_ENGINE_SOCKET"), "Unix domain socket path (e.g. /tmp/flexy_engine.sock)")
	httpPort := flag.String("port", getEnv("PORT", "8091"), "HTTP TCP port")
	redisURL := flag.String("redis", getEnv("REDIS_URL", "redis://localhost:6379/0"), "Redis connection URL")
	flag.Parse()

	// 1. Structured JSON Logger
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}))
	slog.SetDefault(logger)

	slog.Info("Starting flexy-engine...", "port", *httpPort, "socket", *socketPath, "redis", *redisURL)

	// 2. Redis Connection
	opt, err := redis.ParseURL(*redisURL)
	if err != nil {
		slog.Warn("Could not parse REDIS_URL, falling back to localhost:6379", "err", err)
		opt = &redis.Options{Addr: "localhost:6379"}
	}
	opt.DialTimeout = 2 * time.Second
	opt.ReadTimeout = 1 * time.Second
	opt.WriteTimeout = 1 * time.Second

	rdb := redis.NewClient(opt)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Test Redis connection
	pingCtx, pingCancel := context.WithTimeout(ctx, 1*time.Second)
	if err := rdb.Ping(pingCtx).Err(); err != nil {
		slog.Warn("Redis ping failed (engine will use in-memory fallbacks until Redis is available)", "err", err)
	} else {
		slog.Info("Connected to Redis successfully")
	}
	pingCancel()

	// 3. Initialize Services
	cfgStore := config.NewStore(rdb)
	_ = cfgStore.SyncFromRedis(ctx)

	// Background config resync every 30s
	go func() {
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				_ = cfgStore.SyncFromRedis(ctx)
			}
		}
	}()

	locSvc := location.NewService(rdb)
	heatSvc := heatmap.NewService(rdb)

	// Start 10s heatmap broadcast ticker
	go heatSvc.StartHeatmapTicker(ctx, 10*time.Second)

	// 4. WebSocket Hub
	wsHub := ws.NewHub(rdb, getEnv("SECRET_KEY", "flexy-secret-key-fallback"), logger)
	go wsHub.Run(ctx)

	// 5. API Server & WebSocket Multiplexer
	server := api.NewServer(cfgStore, locSvc, heatSvc, rdb, wsHub)
	handler := server.Routes()

	var listeners []net.Listener

	// Listen on Unix domain socket if requested
	if *socketPath != "" {
		_ = os.Remove(*socketPath) // clean up stale socket file
		unixListener, err := net.Listen("unix", *socketPath)
		if err != nil {
			slog.Error("Failed to listen on unix socket", "socket", *socketPath, "err", err)
		} else {
			_ = os.Chmod(*socketPath, 0666) // accessible to daphne/gunicorn user
			listeners = append(listeners, unixListener)
			slog.Info("Listening on Unix domain socket", "path", *socketPath)
		}
	}

	// Always listen on TCP port for development and health probes
	if *httpPort != "" {
		tcpListener, err := net.Listen("tcp", ":"+*httpPort)
		if err != nil {
			slog.Error("Failed to listen on TCP port", "port", *httpPort, "err", err)
		} else {
			listeners = append(listeners, tcpListener)
			slog.Info("Listening on TCP address", "addr", tcpListener.Addr().String())
		}
	}

	if len(listeners) == 0 {
		slog.Error("No valid listeners configured. Exiting.")
		os.Exit(1)
	}

	for _, l := range listeners {
		go func(listener net.Listener) {
			httpServer := &http.Server{
				Handler:      handler,
				ReadTimeout:  5 * time.Second,
				WriteTimeout: 5 * time.Second,
			}
			if err := httpServer.Serve(listener); err != nil && !errors.Is(err, http.ErrServerClosed) {
				slog.Error("Server error", "err", err)
			}
		}(l)
	}

	// 5. Graceful Shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)
	<-quit

	slog.Info("Shutting down flexy-engine...")
	cancel()

	for _, l := range listeners {
		_ = l.Close()
	}
	if *socketPath != "" {
		_ = os.Remove(*socketPath)
	}
	slog.Info("flexy-engine stopped cleanly")
}

func getEnv(key, fallback string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return fallback
}
