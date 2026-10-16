 package pooling

import (
	"errors"
	"math"

	"flexy-engine/internal/geo"
)

const (
	MaxVehicleCapacity = 4
	MaxPickupDistKm    = 4.0 // 4.0 km pickup tolerance
	MaxDropoffDistKm   = 5.0 // 5.0 km dropoff tolerance
	MaxDetourRatio     = 0.40 // Maximum 40% detour
)

// Point represents a geographic coordinate.
type Point struct {
	Lat float64 `json:"lat"`
	Lng float64 `json:"lng"`
}

// ActiveRide represents an in-flight shared ride candidate.
type ActiveRide struct {
	RideID         string  `json:"ride_id"`
	DriverID       string  `json:"driver_id"`
	Status         string  `json:"status"` // "accepted", "arrived", "in_progress"
	CurrentRiders  int     `json:"current_riders"`
	DriverLat      float64 `json:"driver_lat"`
	DriverLng      float64 `json:"driver_lng"`
	PickupLat      float64 `json:"pickup_lat"`
	PickupLng      float64 `json:"pickup_lng"`
	PickupAddress  string  `json:"pickup_address"`
	DropoffLat     float64 `json:"dropoff_lat"`
	DropoffLng     float64 `json:"dropoff_lng"`
	DropoffAddress string  `json:"dropoff_address"`
}

// NewRideRequest represents a new incoming ride requesting carpool/sharing.
type NewRideRequest struct {
	RideID         string  `json:"ride_id"`
	SeatsRequested int     `json:"seats_requested"`
	PickupLat      float64 `json:"pickup_lat"`
	PickupLng      float64 `json:"pickup_lng"`
	PickupAddress  string  `json:"pickup_address"`
	DropoffLat     float64 `json:"dropoff_lat"`
	DropoffLng     float64 `json:"dropoff_lng"`
	DropoffAddress string  `json:"dropoff_address"`
}

// IntermediateStop represents an ordered stop in a pooled route.
type IntermediateStop struct {
	StopOrder int     `json:"stop_order"`
	RideID    string  `json:"ride_id"`
	Action    string  `json:"action"` // "pickup" or "dropoff"
	Address   string  `json:"address"`
	Lat       float64 `json:"lat"`
	Lng       float64 `json:"lng"`
}

// PoolMatchResult contains the matching decision and optimal waypoint stops.
type PoolMatchResult struct {
	Matched          bool               `json:"matched"`
	TargetRideID     string             `json:"target_ride_id"`
	DriverID         string             `json:"driver_id"`
	PickupDistanceKm float64            `json:"pickup_distance_km"`
	DropoffDistanceKm float64           `json:"dropoff_distance_km"`
	DetourRatio      float64            `json:"detour_ratio"`
	TotalDistanceKm  float64            `json:"total_distance_km"`
	OptimalSequence  []IntermediateStop `json:"optimal_sequence"`
	Reason           string             `json:"reason,omitempty"`
}

// EvaluatePoolMatch evaluates whether a new ride can be pooled with an active shared ride.
func EvaluatePoolMatch(active ActiveRide, req NewRideRequest) (*PoolMatchResult, error) {
	seats := req.SeatsRequested
	if seats <= 0 {
		seats = 1
	}

	// 1. Capacity Check
	if active.CurrentRiders+seats > MaxVehicleCapacity {
		return &PoolMatchResult{
			Matched: false,
			Reason:  "vehicle capacity exceeded",
		}, nil
	}

	// 2. Geospatial Proximity Check
	// Pickup distance (km)
	pickupDistMeters := geo.HaversineDistance(active.PickupLat, active.PickupLng, req.PickupLat, req.PickupLng)
	pickupDistKm := pickupDistMeters / 1000.0

	// Dropoff distance (km)
	dropoffDistMeters := geo.HaversineDistance(active.DropoffLat, active.DropoffLng, req.DropoffLat, req.DropoffLng)
	dropoffDistKm := dropoffDistMeters / 1000.0

	if pickupDistKm > MaxPickupDistKm {
		return &PoolMatchResult{
			Matched:          false,
			PickupDistanceKm: math.Round(pickupDistKm*100) / 100,
			Reason:           "pickup distance exceeds 4.0km tolerance",
		}, nil
	}

	if dropoffDistKm > MaxDropoffDistKm {
		return &PoolMatchResult{
			Matched:           false,
			DropoffDistanceKm: math.Round(dropoffDistKm*100) / 100,
			Reason:            "dropoff distance exceeds 5.0km tolerance",
		}, nil
	}

	// 3. Optimal Stop Sequencing and Detour Minimization
	var bestSeq []IntermediateStop
	var bestDist float64 = math.MaxFloat64

	pA := Point{Lat: active.PickupLat, Lng: active.PickupLng}
	dA := Point{Lat: active.DropoffLat, Lng: active.DropoffLng}
	pB := Point{Lat: req.PickupLat, Lng: req.PickupLng}
	dB := Point{Lat: req.DropoffLat, Lng: req.DropoffLng}

	origDistKm := geo.HaversineDistance(pA.Lat, pA.Lng, dA.Lat, dA.Lng) / 1000.0
	if origDistKm <= 0.001 {
		origDistKm = 0.001
	}

	if active.Status == "in_progress" {
		// Passenger A is already in the vehicle.
		// Origin is driver current position.
		curr := Point{Lat: active.DriverLat, Lng: active.DriverLng}
		if curr.Lat == 0 && curr.Lng == 0 {
			curr = pA
		}

		// Candidate 1: Curr -> pB -> dB -> dA (Drop B off before A)
		d1 := (geo.HaversineDistance(curr.Lat, curr.Lng, pB.Lat, pB.Lng) +
			geo.HaversineDistance(pB.Lat, pB.Lng, dB.Lat, dB.Lng) +
			geo.HaversineDistance(dB.Lat, dB.Lng, dA.Lat, dA.Lng)) / 1000.0

		// Candidate 2: Curr -> pB -> dA -> dB (Drop A off before B)
		d2 := (geo.HaversineDistance(curr.Lat, curr.Lng, pB.Lat, pB.Lng) +
			geo.HaversineDistance(pB.Lat, pB.Lng, dA.Lat, dA.Lng) +
			geo.HaversineDistance(dA.Lat, dA.Lng, dB.Lat, dB.Lng)) / 1000.0

		if d1 <= d2 {
			bestDist = d1
			bestSeq = []IntermediateStop{
				{StopOrder: 1, RideID: req.RideID, Action: "pickup", Address: req.PickupAddress, Lat: pB.Lat, Lng: pB.Lng},
				{StopOrder: 2, RideID: req.RideID, Action: "dropoff", Address: req.DropoffAddress, Lat: dB.Lat, Lng: dB.Lng},
				{StopOrder: 3, RideID: active.RideID, Action: "dropoff", Address: active.DropoffAddress, Lat: dA.Lat, Lng: dA.Lng},
			}
		} else {
			bestDist = d2
			bestSeq = []IntermediateStop{
				{StopOrder: 1, RideID: req.RideID, Action: "pickup", Address: req.PickupAddress, Lat: pB.Lat, Lng: pB.Lng},
				{StopOrder: 2, RideID: active.RideID, Action: "dropoff", Address: active.DropoffAddress, Lat: dA.Lat, Lng: dA.Lng},
				{StopOrder: 3, RideID: req.RideID, Action: "dropoff", Address: req.DropoffAddress, Lat: dB.Lat, Lng: dB.Lng},
			}
		}
	} else {
		// Driver has not yet picked up Passenger A.
		// Candidate 1: pA -> pB -> dA -> dB
		d1 := (geo.HaversineDistance(pA.Lat, pA.Lng, pB.Lat, pB.Lng) +
			geo.HaversineDistance(pB.Lat, pB.Lng, dA.Lat, dA.Lng) +
			geo.HaversineDistance(dA.Lat, dA.Lng, dB.Lat, dB.Lng)) / 1000.0

		// Candidate 2: pA -> pB -> dB -> dA
		d2 := (geo.HaversineDistance(pA.Lat, pA.Lng, pB.Lat, pB.Lng) +
			geo.HaversineDistance(pB.Lat, pB.Lng, dB.Lat, dB.Lng) +
			geo.HaversineDistance(dB.Lat, dB.Lng, dA.Lat, dA.Lng)) / 1000.0

		// Candidate 3: pB -> pA -> dA -> dB (If driver is closer to B)
		d3 := (geo.HaversineDistance(pB.Lat, pB.Lng, pA.Lat, pA.Lng) +
			geo.HaversineDistance(pA.Lat, pA.Lng, dA.Lat, dA.Lng) +
			geo.HaversineDistance(dA.Lat, dA.Lng, dB.Lat, dB.Lng)) / 1000.0

		if d1 <= d2 && d1 <= d3 {
			bestDist = d1
			bestSeq = []IntermediateStop{
				{StopOrder: 1, RideID: active.RideID, Action: "pickup", Address: active.PickupAddress, Lat: pA.Lat, Lng: pA.Lng},
				{StopOrder: 2, RideID: req.RideID, Action: "pickup", Address: req.PickupAddress, Lat: pB.Lat, Lng: pB.Lng},
				{StopOrder: 3, RideID: active.RideID, Action: "dropoff", Address: active.DropoffAddress, Lat: dA.Lat, Lng: dA.Lng},
				{StopOrder: 4, RideID: req.RideID, Action: "dropoff", Address: req.DropoffAddress, Lat: dB.Lat, Lng: dB.Lng},
			}
		} else if d2 <= d1 && d2 <= d3 {
			bestDist = d2
			bestSeq = []IntermediateStop{
				{StopOrder: 1, RideID: active.RideID, Action: "pickup", Address: active.PickupAddress, Lat: pA.Lat, Lng: pA.Lng},
				{StopOrder: 2, RideID: req.RideID, Action: "pickup", Address: req.PickupAddress, Lat: pB.Lat, Lng: pB.Lng},
				{StopOrder: 3, RideID: req.RideID, Action: "dropoff", Address: req.DropoffAddress, Lat: dB.Lat, Lng: dB.Lng},
				{StopOrder: 4, RideID: active.RideID, Action: "dropoff", Address: active.DropoffAddress, Lat: dA.Lat, Lng: dA.Lng},
			}
		} else {
			bestDist = d3
			bestSeq = []IntermediateStop{
				{StopOrder: 1, RideID: req.RideID, Action: "pickup", Address: req.PickupAddress, Lat: pB.Lat, Lng: pB.Lng},
				{StopOrder: 2, RideID: active.RideID, Action: "pickup", Address: active.PickupAddress, Lat: pA.Lat, Lng: pA.Lng},
				{StopOrder: 3, RideID: active.RideID, Action: "dropoff", Address: active.DropoffAddress, Lat: dA.Lat, Lng: dA.Lng},
				{StopOrder: 4, RideID: req.RideID, Action: "dropoff", Address: req.DropoffAddress, Lat: dB.Lat, Lng: dB.Lng},
			}
		}
	}

	detourRatio := (bestDist - origDistKm) / origDistKm
	if detourRatio < 0 {
		detourRatio = 0
	}

	return &PoolMatchResult{
		Matched:           true,
		TargetRideID:      active.RideID,
		DriverID:          active.DriverID,
		PickupDistanceKm:  math.Round(pickupDistKm*100) / 100,
		DropoffDistanceKm: math.Round(dropoffDistKm*100) / 100,
		DetourRatio:       math.Round(detourRatio*1000) / 1000,
		TotalDistanceKm:   math.Round(bestDist*100) / 100,
		OptimalSequence:   bestSeq,
	}, nil
}

// FindBestPoolCandidate scans a list of active shared rides and finds the one with the minimal detour.
func FindBestPoolCandidate(candidates []ActiveRide, req NewRideRequest) (*PoolMatchResult, error) {
	if len(candidates) == 0 {
		return nil, errors.New("no active candidates provided")
	}

	var bestResult *PoolMatchResult

	for _, cand := range candidates {
		res, err := EvaluatePoolMatch(cand, req)
		if err != nil || !res.Matched {
			continue
		}

		if bestResult == nil || res.DetourRatio < bestResult.DetourRatio {
			bestResult = res
		}
	}

	if bestResult == nil {
		return &PoolMatchResult{
			Matched: false,
			Reason:  "no compatible shared ride within geospatial/capacity thresholds",
		}, nil
	}

	return bestResult, nil
}
