package pricing

import (
	"math"
	"testing"
	"time"

	"flexy-engine/internal/config"
)

func TestCalculateWaitingFee(t *testing.T) {
	tests := []struct {
		minutes  int
		expected float64
	}{
		{0, 0.0},
		{3, 0.0},
		{5, 0.0},
		{6, 2.0},
		{7, 2.00},
		{10, 2.02}, // 2.0 * 1.002^4 = 2.016 -> 2.02
		{20, 2.06}, // 2.0 * 1.002^14 = 2.0566 -> 2.06
		{30, 2.10}, // 2.0 * 1.002^24 = 2.098 -> 2.10
	}

	for _, tt := range tests {
		actual := CalculateWaitingFee(tt.minutes)
		if math.Abs(actual-tt.expected) > 0.01 {
			t.Errorf("CalculateWaitingFee(%d) = %.2f; expected %.2f", tt.minutes, actual, tt.expected)
		}
	}
}

func TestIsPeakHour(t *testing.T) {
	// Peak 1: 06:30 - 09:00
	t1 := time.Date(2026, 10, 14, 7, 15, 0, 0, time.UTC)
	if !IsPeakHour(t1) {
		t.Errorf("Expected 07:15 to be peak hour")
	}

	// Peak 2: 16:00 - 20:00
	t2 := time.Date(2026, 10, 14, 18, 0, 0, 0, time.UTC)
	if !IsPeakHour(t2) {
		t.Errorf("Expected 18:00 to be peak hour")
	}

	// Off-peak
	t3 := time.Date(2026, 10, 14, 12, 0, 0, 0, time.UTC)
	if IsPeakHour(t3) {
		t.Errorf("Expected 12:00 to NOT be peak hour")
	}
}

func TestComputeFinalFare(t *testing.T) {
	snap := &config.PricingSnapshot{
		DefaultCommissionPct: 10.0,
		Categories: []config.VehicleCategory{
			{Slug: "go", Name: "Flexy Go", BaseFare: 18.0, Multiplier: 1.0, IsActive: true},
			{Slug: "comfort", Name: "Flexy Comfort", BaseFare: 22.0, Multiplier: 1.25, IsActive: true},
		},
		DistanceTiers: []config.DistanceTier{
			{MinKm: 0.0, MaxKm: 5.0, RatePerKm: 6.0, IsActive: true},
			{MinKm: 5.0, MaxKm: 11.0, RatePerKm: 5.0, IsActive: true},
		},
	}

	// 1. Standard 5km Go ride, Subscription driver
	ledger := ComputeFinalFare(
		snap,
		5.0,
		"go",
		nil, nil,
		0,
		"cash",
		0,
		nil,
		false,
		false,
		"subscription",
		false,
	)

	// Base = 18.0, Distance = 5.0 * 6.0 * 1.0 = 30.0 -> Total = 48.0
	if ledger.BaseFare != 18.0 {
		t.Errorf("Expected base fare 18.0, got %.2f", ledger.BaseFare)
	}
	if ledger.DistanceFare != 30.0 {
		t.Errorf("Expected distance fare 30.0, got %.2f", ledger.DistanceFare)
	}
	if ledger.TotalFare != 48.0 {
		t.Errorf("Expected total fare 48.0, got %.2f", ledger.TotalFare)
	}
	// Subscription driver -> 0 commission
	if ledger.CommissionAmount != 0.0 {
		t.Errorf("Expected 0 commission for subscription driver, got %.2f", ledger.CommissionAmount)
	}
	if ledger.DriverPayout != 48.0 {
		t.Errorf("Expected payout 48.0, got %.2f", ledger.DriverPayout)
	}

	// 2. Same ride, Commission driver (10%)
	ledgerComm := ComputeFinalFare(
		snap,
		5.0,
		"go",
		nil, nil,
		0,
		"cash",
		0,
		nil,
		false,
		false,
		"commission",
		false,
	)

	// Total = 48.0 -> 10% commission = 4.80, Driver payout = 43.20
	if ledgerComm.CommissionAmount != 4.80 {
		t.Errorf("Expected commission 4.80, got %.2f", ledgerComm.CommissionAmount)
	}
	if ledgerComm.DriverPayout != 43.20 {
		t.Errorf("Expected driver payout 43.20, got %.2f", ledgerComm.DriverPayout)
	}

	// 3. Commission driver in 14-day free trial -> 0% commission!
	ledgerTrial := ComputeFinalFare(
		snap,
		5.0,
		"go",
		nil, nil,
		0,
		"cash",
		0,
		nil,
		false,
		false,
		"commission",
		true, // In trial
	)

	if ledgerTrial.CommissionAmount != 0.0 {
		t.Errorf("Expected 0 commission for driver in trial, got %.2f", ledgerTrial.CommissionAmount)
	}
	if ledgerTrial.DriverPayout != 48.0 {
		t.Errorf("Expected driver payout 48.0 for driver in trial, got %.2f", ledgerTrial.DriverPayout)
	}

	// 4. Carpooling / Shared Ride Discount (20% off base & distance)
	ledgerShared := ComputeFinalFare(
		snap,
		5.0,
		"go",
		nil, nil,
		0,
		"cash",
		0,
		nil,
		true, // isSharingEnabled
		false,
		"subscription",
		false,
	)

	// Base = 18.0 * 0.8 = 14.40, Distance = 30.0 * 0.8 = 24.00 -> Total = 38.40
	if ledgerShared.BaseFare != 14.40 {
		t.Errorf("Expected shared base fare 14.40, got %.2f", ledgerShared.BaseFare)
	}
	if ledgerShared.DistanceFare != 24.00 {
		t.Errorf("Expected shared distance fare 24.00, got %.2f", ledgerShared.DistanceFare)
	}
	if ledgerShared.TotalFare != 38.40 {
		t.Errorf("Expected shared total fare 38.40, got %.2f", ledgerShared.TotalFare)
	}
}

func TestComputeCourierFare(t *testing.T) {
	catFragile := "cat_fragile"
	wtHeavy := "wt_heavy"

	snap := &config.PricingSnapshot{
		DefaultCommissionPct: 10.0,
		DeliveryVehicleTypes: []config.DeliveryVehicleType{
			{ID: "bike", Name: "Motorbike", BaseFare: 15.0, PerKmRate: 4.0, IsActive: true},
		},
		DeliveryCategories: []config.DeliveryCategory{
			{ID: catFragile, Name: "Fragile", MarkupPercentage: 15.0, IsActive: true},
		},
		DeliveryWeightTiers: []config.DeliveryWeightTier{
			{ID: wtHeavy, Name: "Heavy 5-15kg", MarkupPercentage: 20.0, IsActive: true},
		},
	}

	// 10km bike delivery, surge 1.0, fragile + heavy, commission driver (10%)
	ledger := ComputeCourierFare(
		snap,
		10.0,
		"bike",
		&catFragile,
		&wtHeavy,
		1.0,
		0.0,
		"commission",
		false,
	)

	// Base = 15.0, Distance = 10 * 4 = 40.0 -> Subtotal = 55.0
	// Weight markup = 55.0 * 20% = 11.0
	// Category markup = 55.0 * 15% = 8.25
	// Total = 55.0 + 11.0 + 8.25 = 74.25
	// Commission (10%) = 7.43
	// Driver payout = 74.25 - 7.43 = 66.82
	if ledger.BaseFare != 15.0 {
		t.Errorf("Expected base fare 15.0, got %.2f", ledger.BaseFare)
	}
	if ledger.DistanceFare != 40.0 {
		t.Errorf("Expected distance fare 40.0, got %.2f", ledger.DistanceFare)
	}
	if ledger.TotalFare != 74.25 {
		t.Errorf("Expected total fare 74.25, got %.2f", ledger.TotalFare)
	}
	if ledger.CommissionAmount != 7.43 {
		t.Errorf("Expected commission 7.43, got %.2f", ledger.CommissionAmount)
	}
	if ledger.DriverPayout != 66.82 {
		t.Errorf("Expected driver payout 66.82, got %.2f", ledger.DriverPayout)
	}
}
