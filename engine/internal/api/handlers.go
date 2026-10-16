package api

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"flexy-engine/internal/config"
	"flexy-engine/internal/heatmap"
	"flexy-engine/internal/location"
	"flexy-engine/internal/pooling"
	"flexy-engine/internal/pricing"
	"flexy-engine/internal/tracking"
	"flexy-engine/internal/ws"

	"github.com/redis/go-redis/v9"
)

type Server struct {
	cfgStore  *config.Store
	locSvc    *location.Service
	heatSvc   *heatmap.Service
	rdb       *redis.Client
	wsHub     *ws.Hub
	startTime time.Time
}

func NewServer(cfgStore *config.Store, locSvc *location.Service, heatSvc *heatmap.Service, rdb *redis.Client, wsHub *ws.Hub) *Server {
	return &Server{
		cfgStore:  cfgStore,
		locSvc:    locSvc,
		heatSvc:   heatSvc,
		rdb:       rdb,
		wsHub:     wsHub,
		startTime: time.Now(),
	}
}

func (s *Server) Routes() http.Handler {
	mux := http.NewServeMux()

	// Health & System
	mux.HandleFunc("GET /healthz", s.handleHealthz)

	// Pricing & Surge
	mux.HandleFunc("POST /v1/pricing/surge", s.handleSurge)
	mux.HandleFunc("POST /v1/pricing/estimate", s.handleEstimate)
	mux.HandleFunc("POST /v1/pricing/final", s.handleFinalFare)
	mux.HandleFunc("POST /v1/pricing/courier", s.handleCourierFare)

	// Location Telemetry & Heatmap
	mux.HandleFunc("POST /v1/location/update", s.handleLocationUpdate)
	mux.HandleFunc("GET /v1/heatmap/snapshot", s.handleHeatmapSnapshot)

	// Dispatch & Pooling
	mux.HandleFunc("POST /v1/pooling/match", s.handlePoolingMatch)
	mux.HandleFunc("POST /v1/pooling/evaluate", s.handlePoolingEvaluate)
	mux.HandleFunc("POST /v1/tracking/nearby-drivers", s.handleNearbyDrivers)

	// Dedicated WebSocket Endpoints
	mux.HandleFunc("/ws/rides/global/", s.handleGlobalMapWS)
	mux.HandleFunc("/v1/admin/tracking/ws/", s.handleAdminHeatmapWS)
	mux.HandleFunc("/v1/notifications/ws", s.handleNotificationsWS)
	mux.HandleFunc("/v1/rides/discovery", s.handleRidesDiscoveryWS)
	mux.HandleFunc("/v1/deliveries/discovery", s.handleDeliveriesDiscoveryWS)

	// Dynamic WebSocket Subpaths for Ride and Delivery Tracking
	mux.HandleFunc("/v1/rides/", s.handleRidesDynamic)
	mux.HandleFunc("/v1/deliveries/", s.handleDeliveriesDynamic)

	return withRecoveryAndLogging(mux)
}

func (s *Server) handleHealthz(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":         "healthy",
		"service":        "flexy-engine",
		"uptime_seconds": int(time.Since(s.startTime).Seconds()),
	})
}

// ── WebSocket Handlers ────────────────────────────────────────────────────────

func (s *Server) handleGlobalMapWS(w http.ResponseWriter, r *http.Request) {
	if s.wsHub == nil {
		writeError(w, http.StatusServiceUnavailable, "ws hub not initialized")
		return
	}
	ws.ServeGlobalMapHandler(s.wsHub, w, r)
}

func (s *Server) handleAdminHeatmapWS(w http.ResponseWriter, r *http.Request) {
	if s.wsHub == nil {
		writeError(w, http.StatusServiceUnavailable, "ws hub not initialized")
		return
	}
	ws.ServeAdminHeatmapHandler(s.wsHub, w, r)
}

func (s *Server) handleNotificationsWS(w http.ResponseWriter, r *http.Request) {
	if s.wsHub == nil {
		writeError(w, http.StatusServiceUnavailable, "ws hub not initialized")
		return
	}
	ws.ServeNotificationsHandler(s.wsHub, w, r)
}

func (s *Server) handleRidesDiscoveryWS(w http.ResponseWriter, r *http.Request) {
	if s.wsHub == nil {
		writeError(w, http.StatusServiceUnavailable, "ws hub not initialized")
		return
	}
	ws.ServeDiscoveryHandler(s.wsHub, w, r, "rides")
}

func (s *Server) handleDeliveriesDiscoveryWS(w http.ResponseWriter, r *http.Request) {
	if s.wsHub == nil {
		writeError(w, http.StatusServiceUnavailable, "ws hub not initialized")
		return
	}
	ws.ServeDiscoveryHandler(s.wsHub, w, r, "deliveries")
}

func (s *Server) handleRidesDynamic(w http.ResponseWriter, r *http.Request) {
	if s.wsHub == nil {
		writeError(w, http.StatusServiceUnavailable, "ws hub not initialized")
		return
	}

	// Path format: /v1/rides/{ride_id}/track/{role}
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) >= 4 && parts[0] == "v1" && parts[1] == "rides" && parts[3] == "track" {
		rideID := parts[2]
		role := parts[4] // "rider" or "driver"
		ws.ServeRideTrackingHandler(s.wsHub, w, r, rideID, role)
		return
	}

	http.NotFound(w, r)
}

func (s *Server) handleDeliveriesDynamic(w http.ResponseWriter, r *http.Request) {
	if s.wsHub == nil {
		writeError(w, http.StatusServiceUnavailable, "ws hub not initialized")
		return
	}

	// Path format: /v1/deliveries/{delivery_id}/track/{role}
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) >= 4 && parts[0] == "v1" && parts[1] == "deliveries" && parts[3] == "track" {
		deliveryID := parts[2]
		role := parts[4] // "sender" or "courier"
		ws.ServeDeliveryTrackingHandler(s.wsHub, w, r, deliveryID, role)
		return
	}

	http.NotFound(w, r)
}

// ── Pooling Handlers ──────────────────────────────────────────────────────────

type PoolMatchBatchRequest struct {
	ActiveCandidates []pooling.ActiveRide   `json:"active_candidates"`
	NewRide          pooling.NewRideRequest `json:"new_ride"`
}

func (s *Server) handlePoolingMatch(w http.ResponseWriter, r *http.Request) {
	var req PoolMatchBatchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return
	}

	res, err := pooling.FindBestPoolCandidate(req.ActiveCandidates, req.NewRide)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, res)
}

type PoolEvaluateRequest struct {
	ActiveRide pooling.ActiveRide   `json:"active_ride"`
	NewRide    pooling.NewRideRequest `json:"new_ride"`
}

func (s *Server) handlePoolingEvaluate(w http.ResponseWriter, r *http.Request) {
	var req PoolEvaluateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return
	}

	res, err := pooling.EvaluatePoolMatch(req.ActiveRide, req.NewRide)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, res)
}

// ── Tracking & Nearby Drivers Handlers ────────────────────────────────────────

func (s *Server) handleNearbyDrivers(w http.ResponseWriter, r *http.Request) {
	var req tracking.NearbyDriversRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return
	}

	res, err := tracking.FindNearbyDrivers(r.Context(), s.rdb, req)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "nearby search error: "+err.Error())
		return
	}

	writeJSON(w, http.StatusOK, res)
}

// ── Pricing Handlers ──────────────────────────────────────────────────────────

type SurgeRequest struct {
	Lat                  *float64   `json:"lat"`
	Lng                  *float64   `json:"lng"`
	RadiusKm             float64    `json:"radius_km"`
	DurationSec          *int       `json:"duration_sec"`
	DurationInTrafficSec *int       `json:"duration_in_traffic_sec"`
	WeatherSurge         float64    `json:"weather_surge"`
	TargetTime           *time.Time `json:"target_time"`
}

func (s *Server) handleSurge(w http.ResponseWriter, r *http.Request) {
	var req SurgeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return
	}

	snap := s.cfgStore.Get()
	multiplier := pricing.CalculateSurge(
		r.Context(),
		s.rdb,
		snap,
		req.Lat, req.Lng,
		req.RadiusKm,
		req.DurationSec,
		req.DurationInTrafficSec,
		req.WeatherSurge,
		req.TargetTime,
	)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"surge_multiplier": multiplier,
	})
}

type EstimateRequest struct {
	DistanceKm       float64 `json:"distance_km"`
	SurgeMultiplier  float64 `json:"surge_multiplier"`
	NumStops         int     `json:"num_stops"`
	IsSharingEnabled bool    `json:"is_sharing_enabled"`
}

func (s *Server) handleEstimate(w http.ResponseWriter, r *http.Request) {
	var req EstimateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return
	}

	snap := s.cfgStore.Get()
	estimates := pricing.CalculateFareEstimates(
		snap,
		req.DistanceKm,
		req.SurgeMultiplier,
		req.NumStops,
		req.IsSharingEnabled,
	)

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"estimates": estimates,
	})
}

type FinalFareRequest struct {
	DistanceKm          float64  `json:"distance_km"`
	VehicleCategorySlug string   `json:"vehicle_category_slug"`
	Lat                 *float64 `json:"lat"`
	Lng                 *float64 `json:"lng"`
	WaitingMinutes      int      `json:"waiting_minutes"`
	PaymentMethod       string   `json:"payment_method"`
	NumStops            int      `json:"num_stops"`
	SurgeOverride       *float64 `json:"surge_override"`
	IsSharingEnabled    bool     `json:"is_sharing_enabled"`
	IsCancelled         bool     `json:"is_cancelled"`
	DriverBillingModel  string   `json:"driver_billing_model"`
	IsDriverInTrial     bool     `json:"is_driver_in_trial"`
}

func (s *Server) handleFinalFare(w http.ResponseWriter, r *http.Request) {
	var req FinalFareRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return
	}

	snap := s.cfgStore.Get()
	ledger := pricing.ComputeFinalFare(
		snap,
		req.DistanceKm,
		req.VehicleCategorySlug,
		req.Lat, req.Lng,
		req.WaitingMinutes,
		req.PaymentMethod,
		req.NumStops,
		req.SurgeOverride,
		req.IsSharingEnabled,
		req.IsCancelled,
		req.DriverBillingModel,
		req.IsDriverInTrial,
	)

	writeJSON(w, http.StatusOK, ledger)
}

type CourierFareRequest struct {
	DistanceKm         float64 `json:"distance_km"`
	VehicleTypeID      string  `json:"vehicle_type_id"`
	CategoryID         *string `json:"category_id"`
	WeightTierID       *string `json:"weight_tier_id"`
	SurgeMultiplier    float64 `json:"surge_multiplier"`
	PromoDiscount      float64 `json:"promo_discount"`
	DriverBillingModel string  `json:"driver_billing_model"`
	IsDriverInTrial    bool    `json:"is_driver_in_trial"`
}

func (s *Server) handleCourierFare(w http.ResponseWriter, r *http.Request) {
	var req CourierFareRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return
	}

	snap := s.cfgStore.Get()
	ledger := pricing.ComputeCourierFare(
		snap,
		req.DistanceKm,
		req.VehicleTypeID,
		req.CategoryID,
		req.WeightTierID,
		req.SurgeMultiplier,
		req.PromoDiscount,
		req.DriverBillingModel,
		req.IsDriverInTrial,
	)

	writeJSON(w, http.StatusOK, ledger)
}

func (s *Server) handleLocationUpdate(w http.ResponseWriter, r *http.Request) {
	var req location.LocationUpdatePayload
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body: "+err.Error())
		return
	}

	if err := s.locSvc.IngestLocation(r.Context(), req); err != nil {
		writeError(w, http.StatusInternalServerError, "failed to ingest location: "+err.Error())
		return
	}

	// Also broadcast location to WebSocket hub if active
	if s.wsHub != nil && req.DriverID != "" {
		locBytes, _ := json.Marshal(map[string]interface{}{
			"driver_id": req.DriverID,
			"latitude":  req.Lat,
			"longitude": req.Lng,
			"timestamp": req.Timestamp,
		})
		s.wsHub.BroadcastToRoom("global_rides", "driver_location", locBytes, req.DriverID)
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleHeatmapSnapshot(w http.ResponseWriter, r *http.Request) {
	markers, err := s.heatSvc.GetSnapshot(r.Context())
	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to get snapshot: "+err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"markers": markers,
	})
}

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(data); err != nil {
		slog.Error("failed to write json response", "err", err)
	}
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func withRecoveryAndLogging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		defer func() {
			if rec := recover(); rec != nil {
				slog.Error("panic recovered in handler", "panic", rec, "path", r.URL.Path)
				writeError(w, http.StatusInternalServerError, fmt.Sprintf("internal server error: %v", rec))
			}
		}()
		next.ServeHTTP(w, r)
		duration := time.Since(start)
		if duration > 50*time.Millisecond {
			slog.Warn("slow request", "method", r.Method, "path", r.URL.Path, "duration_ms", duration.Milliseconds())
		}
	})
}
