package tracking

import (
	"context"
	"math"
	"sort"
	"strconv"

	"flexy-engine/internal/geo"
	"github.com/redis/go-redis/v9"
)

// DriverCandidate represents a nearby eligible driver.
type DriverCandidate struct {
	DriverID      string  `json:"driver_id"`
	DistanceKm    float64 `json:"distance_km"`
	Latitude      float64 `json:"latitude"`
	Longitude     float64 `json:"longitude"`
	IsMovingAway  bool    `json:"is_moving_away"`
}

// NearbyDriversRequest represents the dispatch query.
type NearbyDriversRequest struct {
	PickupLat         float64            `json:"pickup_lat"`
	PickupLng         float64            `json:"pickup_lng"`
	AttemptCount      int                `json:"attempt_count"`
	ExcludedDriverIDs []string           `json:"excluded_driver_ids"`
	DistanceHistory   map[string]float64 `json:"distance_history"` // driver_id -> prev_dist_km
}

// NearbyDriversResponse returns sorted candidate drivers.
type NearbyDriversResponse struct {
	RadiusKm    float64           `json:"radius_km"`
	Attempt     int               `json:"attempt"`
	Drivers     []DriverCandidate `json:"drivers"`
	TotalFound  int               `json:"total_found"`
	MovingAway  []string          `json:"moving_away_ids"`
}

// CalculateAdaptiveRadius returns the search radius based on dispatch attempt.
func CalculateAdaptiveRadius(attempt int) float64 {
	radius := 3.0 + (float64(attempt) * 1.5)
	if radius > 15.0 {
		return 15.0
	}
	return radius
}

// FindNearbyDrivers searches Redis GEO driver_locations within adaptive radius.
func FindNearbyDrivers(ctx context.Context, rdb *redis.Client, req NearbyDriversRequest) (*NearbyDriversResponse, error) {
	radius := CalculateAdaptiveRadius(req.AttemptCount)

	excludedMap := make(map[string]bool)
	for _, id := range req.ExcludedDriverIDs {
		excludedMap[id] = true
	}

	var candidates []DriverCandidate
	var movingAwayIDs []string

	if rdb != nil {
		// Use Redis GEOSEARCH
		locations, err := rdb.GeoSearchLocation(ctx, "driver_locations", &redis.GeoSearchLocationQuery{
			GeoSearchQuery: redis.GeoSearchQuery{
				Longitude:  req.PickupLng,
				Latitude:   req.PickupLat,
				Radius:     radius,
				RadiusUnit: "km",
				Sort:       "asc",
			},
			WithCoord: true,
			WithDist:  true,
		}).Result()

		if err == nil {
			for _, loc := range locations {
				driverID := loc.Name
				if excludedMap[driverID] {
					continue
				}

				distKm := loc.Dist
				if distKm == 0 && (loc.Latitude != 0 || loc.Longitude != 0) {
					distKm = geo.HaversineDistance(req.PickupLat, req.PickupLng, loc.Latitude, loc.Longitude) / 1000.0
				}
				// Check displacement / moving away check
				isMovingAway := false
				if prevDist, exists := req.DistanceHistory[driverID]; exists {
					if distKm > prevDist+0.15 { // Moved away by > 150m
						isMovingAway = true
						movingAwayIDs = append(movingAwayIDs, driverID)
					}
				}

				candidates = append(candidates, DriverCandidate{
					DriverID:     driverID,
					DistanceKm:   math.Round(distKm*100) / 100,
					Latitude:     loc.Latitude,
					Longitude:    loc.Longitude,
					IsMovingAway: isMovingAway,
				})
			}
		}
	}

	// Filter out moving away drivers from primary target list
	var eligible []DriverCandidate
	for _, c := range candidates {
		if !c.IsMovingAway {
			eligible = append(eligible, c)
		}
	}

	// Sort eligible drivers by distance ascending
	sort.Slice(eligible, func(i, j int) bool {
		return eligible[i].DistanceKm < eligible[j].DistanceKm
	})

	return &NearbyDriversResponse{
		RadiusKm:   radius,
		Attempt:    req.AttemptCount,
		Drivers:    eligible,
		TotalFound: len(eligible),
		MovingAway: movingAwayIDs,
	}, nil
}

// IngestDriverCoordinates updates Redis GEO index and queues telemetry.
func IngestDriverCoordinates(ctx context.Context, rdb *redis.Client, driverID string, lat, lng, heading, speed float64) error {
	if rdb == nil {
		return nil
	}

	_, err := rdb.GeoAdd(ctx, "driver_locations", &redis.GeoLocation{
		Name:      driverID,
		Longitude: lng,
		Latitude:  lat,
	}).Result()

	return err
}

// ParseDriverID converts int or string ID to string.
func ParseDriverID(val interface{}) string {
	switch v := val.(type) {
	case string:
		return v
	case int:
		return strconv.Itoa(v)
	case float64:
		return strconv.Itoa(int(v))
	default:
		return ""
	}
}
