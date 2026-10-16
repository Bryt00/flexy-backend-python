package heatmap

import (
	"context"
	"encoding/json"
	"log/slog"
	"math"
	"time"

	"github.com/redis/go-redis/v9"
)

type Marker struct {
	DriverID  string  `json:"driver_id"`
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
}

type Service struct {
	rdb *redis.Client
}

func NewService(rdb *redis.Client) *Service {
	return &Service{rdb: rdb}
}

// GetSnapshot retrieves online drivers with coordinates rounded to 4 decimals, capped at 500
func (s *Service) GetSnapshot(ctx context.Context) ([]Marker, error) {
	if s.rdb == nil {
		return []Marker{}, nil
	}

	// Fetch up to 500 drivers from Redis driver_locations
	// Center around Ghana (-0.1870, 5.6037) or wide bounding radius (e.g. 1000km)
	results, err := s.rdb.GeoRadius(ctx, "driver_locations", -0.1870, 5.6037, &redis.GeoRadiusQuery{
		Radius:    1000,
		Unit:      "km",
		WithCoord: true,
		Count:     500,
		Sort:      "ASC",
	}).Result()

	if err != nil {
		return nil, err
	}

	markers := make([]Marker, 0, len(results))
	for _, res := range results {
		markers = append(markers, Marker{
			DriverID:  res.Name,
			Latitude:  round4(res.Latitude),
			Longitude: round4(res.Longitude),
		})
	}
	return markers, nil
}

// StartHeatmapTicker runs a background loop every 10 seconds broadcasting the heatmap
func (s *Service) StartHeatmapTicker(ctx context.Context, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			markers, err := s.GetSnapshot(ctx)
			if err != nil {
				slog.Debug("Heatmap ticker snapshot error", "err", err)
				continue
			}

			if len(markers) > 0 {
				payload, _ := json.Marshal(map[string]interface{}{
					"type": "heatmap_update",
					"data": markers,
				})
				// Broadcast on Redis channel for Django Channels custom layer
				_ = s.rdb.Publish(ctx, "admin_heatmap", payload).Err()
			}
		}
	}
}

func round4(val float64) float64 {
	return math.Round(val*10000.0) / 10000.0
}
