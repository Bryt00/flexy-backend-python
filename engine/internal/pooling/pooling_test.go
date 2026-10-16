package pooling

import (
	"testing"
)

func TestEvaluatePoolMatch_Success(t *testing.T) {
	// Active ride from Accra Mall to Airport (close proximity)
	active := ActiveRide{
		RideID:         "ride-active-1",
		DriverID:       "driver-101",
		Status:         "accepted",
		CurrentRiders:  1,
		PickupLat:      5.622,
		PickupLng:      -0.173, // Accra Mall
		PickupAddress:  "Accra Mall, Tetteh Quarshie",
		DropoffLat:     5.605,
		DropoffLng:     -0.166, // Kotoka Airport
		DropoffAddress: "Kotoka International Airport",
	}

	// New ride from Marina Mall to Airport Junction (within 2km of both)
	req := NewRideRequest{
		RideID:         "ride-new-2",
		SeatsRequested: 1,
		PickupLat:      5.610,
		PickupLng:      -0.178, // Marina Mall (~1.4km from Accra Mall)
		PickupAddress:  "Marina Mall, Airport",
		DropoffLat:     5.602,
		DropoffLng:     -0.168, // Airport Junction (~0.4km from Airport)
		DropoffAddress: "Airport Bypass Road",
	}

	res, err := EvaluatePoolMatch(active, req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !res.Matched {
		t.Fatalf("expected pool match to succeed, got false with reason: %s", res.Reason)
	}
	if res.TargetRideID != "ride-active-1" {
		t.Errorf("expected TargetRideID to be ride-active-1, got %s", res.TargetRideID)
	}
	if res.DriverID != "driver-101" {
		t.Errorf("expected DriverID to be driver-101, got %s", res.DriverID)
	}
	if len(res.OptimalSequence) != 4 {
		t.Errorf("expected 4 waypoint stops, got %d", len(res.OptimalSequence))
	}
}

func TestEvaluatePoolMatch_CapacityExceeded(t *testing.T) {
	active := ActiveRide{
		RideID:        "ride-active-full",
		CurrentRiders: 4, // Already at max 4
		PickupLat:     5.622,
		PickupLng:     -0.173,
		DropoffLat:    5.605,
		DropoffLng:    -0.166,
	}

	req := NewRideRequest{
		RideID:         "ride-new-seats",
		SeatsRequested: 1,
		PickupLat:      5.622,
		PickupLng:      -0.173,
		DropoffLat:     5.605,
		DropoffLng:     -0.166,
	}

	res, err := EvaluatePoolMatch(active, req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res.Matched {
		t.Errorf("expected match to fail due to capacity, but got true")
	}
}

func TestEvaluatePoolMatch_PickupTooFar(t *testing.T) {
	active := ActiveRide{
		RideID:        "ride-active-accra",
		CurrentRiders: 1,
		PickupLat:     5.622,
		PickupLng:     -0.173, // Accra
		DropoffLat:    5.605,
		DropoffLng:    -0.166,
	}

	// Request in Tema (~20km away)
	req := NewRideRequest{
		RideID:         "ride-new-tema",
		SeatsRequested: 1,
		PickupLat:      5.670,
		PickupLng:      -0.010, // Tema
		DropoffLat:     5.605,
		DropoffLng:     -0.166,
	}

	res, err := EvaluatePoolMatch(active, req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if res.Matched {
		t.Errorf("expected match to fail due to pickup distance, but got true")
	}
}

func TestEvaluatePoolMatch_InProgressRide(t *testing.T) {
	active := ActiveRide{
		RideID:         "ride-in-flight",
		DriverID:       "driver-55",
		Status:         "in_progress",
		CurrentRiders:  1,
		DriverLat:      5.618,
		DriverLng:      -0.171,
		PickupLat:      5.622,
		PickupLng:      -0.173,
		DropoffLat:     5.590,
		DropoffLng:     -0.160,
		DropoffAddress: "Osu Oxford Street",
	}

	req := NewRideRequest{
		RideID:         "ride-new-3",
		SeatsRequested: 1,
		PickupLat:      5.612,
		PickupLng:      -0.170, // On the way to Osu
		PickupAddress:  "Airport Residential",
		DropoffLat:     5.592,
		DropoffLng:     -0.162, // Close to Osu
		DropoffAddress: "Danquah Circle",
	}

	res, err := EvaluatePoolMatch(active, req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !res.Matched {
		t.Fatalf("expected in-flight pool match to succeed, got %s", res.Reason)
	}
	if len(res.OptimalSequence) != 3 {
		t.Errorf("expected 3 remaining waypoints (pickup B, drop B, drop A), got %d", len(res.OptimalSequence))
	}
}
