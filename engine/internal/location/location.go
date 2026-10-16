package location

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

type LocationUpdatePayload struct {
	DriverID  string    `json:"driver_id"` // canonical Profile ID
	UserID    string    `json:"user_id,omitempty"`
	Lat       float64   `json:"lat"`
	Lng       float64   `json:"lng"`
	Timestamp time.Time `json:"timestamp"`
}

type Service struct {
	rdb *redis.Client
}

func NewService(rdb *redis.Client) *Service {
	return &Service{rdb: rdb}
}

// IngestLocation updates the geospatial index, queues write-behind batch DB update,
// and publishes real-time location to the global stream.
func (s *Service) IngestLocation(ctx context.Context, p LocationUpdatePayload) error {
	if s.rdb == nil {
		return fmt.Errorf("redis client not configured")
	}

	if p.Timestamp.IsZero() {
		p.Timestamp = time.Now()
	}

	pipe := s.rdb.Pipeline()

	// 1. Update Geospatial Index
	pipe.GeoAdd(ctx, "driver_locations", &redis.GeoLocation{
		Name:      p.DriverID,
		Latitude:  p.Lat,
		Longitude: p.Lng,
	})

	// 2. Queue write-behind for PostgreSQL batch flushing
	queueItem, _ := json.Marshal(map[string]interface{}{
		"driver_id": p.DriverID,
		"lat":       p.Lat,
		"lng":       p.Lng,
		"timestamp": float64(p.Timestamp.UnixNano()) / 1e9,
	})
	pipe.RPush(ctx, "driver_location_updates_queue", string(queueItem))

	// 3. Publish to Channels-compatible broadcast channel if requested
	broadcastData, _ := json.Marshal(map[string]interface{}{
		"type": "broadcast_location",
		"data": map[string]interface{}{
			"driver_id": p.DriverID,
			"lat":       p.Lat,
			"lng":       p.Lng,
		},
	})
	pipe.Publish(ctx, "global_rides", broadcastData)

	_, err := pipe.Exec(ctx)
	return err
}
