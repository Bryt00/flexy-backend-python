package tracking

import (
	"context"
	"testing"
)

func TestCalculateAdaptiveRadius(t *testing.T) {
	tests := []struct {
		attempt int
		want    float64
	}{
		{0, 3.0},
		{1, 4.5},
		{2, 6.0},
		{4, 9.0},
		{8, 15.0},
		{10, 15.0}, // Capped at 15km
	}

	for _, tt := range tests {
		got := CalculateAdaptiveRadius(tt.attempt)
		if got != tt.want {
			t.Errorf("CalculateAdaptiveRadius(%d) = %v; want %v", tt.attempt, got, tt.want)
		}
	}
}

func TestFindNearbyDrivers_MovingAwayFilter(t *testing.T) {
	ctx := context.Background()
	req := NearbyDriversRequest{
		PickupLat:    5.6037,
		PickupLng:    -0.1870,
		AttemptCount: 0,
		DistanceHistory: map[string]float64{
			"driver_moving_away": 1.0, // previously 1.0km, will be tested with mock or empty redis
		},
	}

	resp, err := FindNearbyDrivers(ctx, nil, req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.RadiusKm != 3.0 {
		t.Errorf("expected radius 3.0km on attempt 0, got %v", resp.RadiusKm)
	}
}
