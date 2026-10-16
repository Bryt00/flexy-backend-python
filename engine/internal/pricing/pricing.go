package pricing

import (
	"context"
	"math"
	"strings"
	"time"

	"flexy-engine/internal/config"
	"flexy-engine/internal/geo"

	"github.com/redis/go-redis/v9"
)

// FareLedger represents the finalized 9-stage ledger returned by the engine
type FareLedger struct {
	BaseFare               float64 `json:"base_fare"`
	DistanceFare           float64 `json:"distance_fare"`
	StopsFee               float64 `json:"stops_fee"`
	WaitingFee             float64 `json:"waiting_fee"`
	CancellationFee        float64 `json:"cancellation_fee"`
	SurgeMultiplier        float64 `json:"surge_multiplier"`
	TotalFare              float64 `json:"total_fare"`
	BillingModel           string  `json:"billing_model"`            // "subscription" or "commission"
	CommissionRate         float64 `json:"commission_rate"`          // e.g. 10.0
	CommissionFlat         float64 `json:"commission_flat"`          // optional flat fee
	CommissionAmount       float64 `json:"commission_amount"`        // calculated commission in GHS
	DriverPayout           float64 `json:"driver_payout"`            // total_fare - commission_amount
	IsInTrial              bool    `json:"is_in_trial"`              // 14-day trial flag
}

// CourierFareLedger represents the ledger for courier deliveries
type CourierFareLedger struct {
	BaseFare         float64 `json:"base_fare"`
	DistanceFare     float64 `json:"distance_fare"`
	SurgeMultiplier  float64 `json:"surge_multiplier"`
	WeightMarkup     float64 `json:"weight_markup"`
	CategoryMarkup   float64 `json:"category_markup"`
	DiscountAmount   float64 `json:"discount_amount"`
	TotalFare        float64 `json:"total_fare"`
	BillingModel     string  `json:"billing_model"`
	CommissionRate   float64 `json:"commission_rate"`
	CommissionAmount float64 `json:"commission_amount"`
	DriverPayout     float64 `json:"driver_payout"`
}

// SurgePoint represents a coordinate and multiplier for surge heatmaps
type SurgePoint struct {
	Lat        float64 `json:"lat"`
	Lng        float64 `json:"lng"`
	Multiplier float64 `json:"multiplier"`
}

// CalculateWaitingFee implements:
// - First 5 mins: FREE
// - After 5 mins: Flat GHS 2 + 0.2% compound growth per minute on the fee itself
// Formula: 2.0 * math.Pow(1.002, paid_minutes - 1)
func CalculateWaitingFee(waitingMinutes int) float64 {
	if waitingMinutes <= 5 {
		return 0.0
	}
	paidMinutes := float64(waitingMinutes - 5)
	fee := 2.0
	if paidMinutes > 1 {
		fee = 2.0 * math.Pow(1.002, paidMinutes-1.0)
	}
	return round2(fee)
}

// IsPeakHour checks Bolt Ghana-equivalent peak windows: 06:30 - 09:00 and 16:00 - 20:00
func IsPeakHour(t time.Time) bool {
	hour := t.Hour()
	min := t.Minute()
	totalMin := hour*60 + min

	peak1Start := 6*60 + 30
	peak1End := 9 * 60
	peak2Start := 16 * 60
	peak2End := 20 * 60

	return (totalMin >= peak1Start && totalMin <= peak1End) ||
		(totalMin >= peak2Start && totalMin <= peak2End)
}

// FindMatchingPricingRule resolves the most relevant pricing rule by city proximity
func FindMatchingPricingRule(rules []config.PricingRule, lat, lng *float64) *config.PricingRule {
	if len(rules) == 0 {
		return nil
	}
	if lat != nil && lng != nil {
		minDist := math.MaxFloat64
		var bestRule *config.PricingRule
		for i := range rules {
			r := &rules[i]
			if r.CityIsActive && r.CityLat != nil && r.CityLng != nil {
				distKm := geo.HaversineKm(*lat, *lng, *r.CityLat, *r.CityLng)
				if distKm < 100.0 && distKm < minDist {
					minDist = distKm
					bestRule = r
				}
			}
		}
		if bestRule != nil {
			return bestRule
		}
	}

	// Fallback to global rule without city
	for i := range rules {
		if rules[i].CityID == nil {
			return &rules[i]
		}
	}
	return &rules[0]
}

// CalculateSurge computes the combined surge multiplier
func CalculateSurge(
	ctx context.Context,
	rdb *redis.Client,
	snap *config.PricingSnapshot,
	lat, lng *float64,
	radiusKm float64,
	durationSec, durationInTrafficSec *int,
	weatherSurge float64,
	targetTime *time.Time,
) float64 {
	multiplier := 1.0

	if targetTime == nil {
		now := time.Now()
		targetTime = &now
	}

	rule := FindMatchingPricingRule(snap.PricingRules, lat, lng)
	enableWeather := true
	maxWeather := 1.5
	enableTraffic := true
	maxTraffic := 1.5

	// Step 1: Admin-set rule surge
	if rule != nil {
		enableWeather = rule.EnableWeatherSurge
		maxWeather = rule.MaxWeatherSurge
		enableTraffic = rule.EnableTrafficSurge
		maxTraffic = rule.MaxTrafficSurge

		rawSurge := rule.SurgeMultiplier
		scaledSurge := rawSurge
		if rawSurge > 3.0 {
			scaledSurge = rawSurge / 10.0
		}
		if scaledSurge > multiplier {
			multiplier = scaledSurge
		}
	}

	// Step 2: Peak Hour Surge (1.3x)
	if IsPeakHour(*targetTime) {
		if 1.3 > multiplier {
			multiplier = 1.3
		}
	}

	// Step 2.5: Environmental Surge (Weather & Traffic)
	envSurge := 1.0
	if enableWeather && weatherSurge > 1.0 {
		wSurge := weatherSurge
		if wSurge > maxWeather {
			wSurge = maxWeather
		}
		if wSurge > envSurge {
			envSurge = wSurge
		}
	}

	if enableTraffic && durationSec != nil && durationInTrafficSec != nil && *durationSec > 0 {
		if *durationInTrafficSec > *durationSec {
			delayRatio := float64(*durationInTrafficSec) / float64(*durationSec)
			if delayRatio > 1.2 {
				tSurge := 1.0 + ((delayRatio - 1.2) / 2.0)
				if tSurge > maxTraffic {
					tSurge = maxTraffic
				}
				if tSurge > envSurge {
					envSurge = tSurge
				}
			}
		}
	}
	if envSurge > multiplier {
		multiplier = envSurge
	}

	// Step 3: Dynamic Spatial Demand Surge from Redis
	if rdb != nil && lat != nil && lng != nil {
		if radiusKm <= 0 {
			radiusKm = 5.0
		}
		drivers, err := rdb.GeoRadius(ctx, "driver_locations", *lng, *lat, &redis.GeoRadiusQuery{
			Radius: radiusKm,
			Unit:   "km",
		}).Result()
		if err == nil {
			requests, rErr := rdb.GeoRadius(ctx, "ride_requests", *lng, *lat, &redis.GeoRadiusQuery{
				Radius: radiusKm,
				Unit:   "km",
			}).Result()
			if rErr == nil && len(requests) > 0 {
				drCount := len(drivers)
				rqCount := len(requests)
				if drCount == 0 {
					if 2.0 > multiplier {
						multiplier = 2.0
					}
				} else {
					ratio := float64(rqCount) / float64(drCount)
					if ratio >= 3.0 {
						if 1.8 > multiplier {
							multiplier = 1.8
						}
					} else if ratio >= 1.5 {
						if 1.5 > multiplier {
							multiplier = 1.5
						}
					}
				}
			}
		}
	}

	return round2(multiplier)
}

// ComputeFinalFare computes the 9-stage fare ledger for passenger rides
func ComputeFinalFare(
	snap *config.PricingSnapshot,
	distanceKm float64,
	vehicleCategorySlug string,
	lat, lng *float64,
	waitingMinutes int,
	paymentMethod string,
	numStops int,
	surgeOverride *float64,
	isSharingEnabled bool,
	isCancelled bool,
	driverBillingModel string, // "subscription" or "commission"
	isDriverInTrial bool,
) FareLedger {
	ledger := FareLedger{
		BillingModel:    driverBillingModel,
		IsInTrial:       isDriverInTrial,
		SurgeMultiplier: 1.0,
	}
	if ledger.BillingModel == "" {
		ledger.BillingModel = "subscription"
	}

	// Find category
	var category *config.VehicleCategory
	for i := range snap.Categories {
		if snap.Categories[i].Slug == vehicleCategorySlug {
			category = &snap.Categories[i]
			break
		}
	}
	if category == nil {
		// Default fallback to first active category or standard
		for i := range snap.Categories {
			if snap.Categories[i].IsActive {
				category = &snap.Categories[i]
				break
			}
		}
	}
	if category == nil {
		return ledger
	}

	rule := FindMatchingPricingRule(snap.PricingRules, lat, lng)

	// Stage 1: Base Fare
	if rule != nil && rule.BaseFare > 0 {
		ledger.BaseFare = rule.BaseFare * category.Multiplier
	} else {
		ledger.BaseFare = category.BaseFare
	}

	// Stage 2 & 3: Distance Charges + Category Multiplier
	var tieredDistCharge float64
	if rule != nil && rule.PerKmRate > 0 {
		tieredDistCharge = distanceKm * rule.PerKmRate * category.Multiplier
	} else {
		remainingDist := distanceKm
		for _, tier := range snap.DistanceTiers {
			if !tier.IsActive || remainingDist <= 0 {
				continue
			}
			tierRange := tier.MaxKm - tier.MinKm
			distInTier := math.Min(remainingDist, tierRange)
			scaledRate := tier.RatePerKm * category.Multiplier
			tieredDistCharge += distInTier * scaledRate
			remainingDist -= distInTier
		}
	}

	// Stage 4: Apply Surge Multiplier (To km-based distance charge only)
	if surgeOverride != nil {
		ledger.SurgeMultiplier = *surgeOverride
	}
	ledger.DistanceFare = tieredDistCharge * ledger.SurgeMultiplier

	// Stage 5: Stops Fee (GHS 2.0 per extra stop)
	if numStops > 0 {
		ledger.StopsFee = float64(numStops) * 2.0
	}

	// Stage 6: Waiting Fee
	ledger.WaitingFee = CalculateWaitingFee(waitingMinutes)

	// Stage 7: Cancellation Logic
	if isCancelled {
		pm := strings.ToLower(paymentMethod)
		if pm == "card" || pm == "momo" || pm == "wallet" {
			ledger.CancellationFee = 8.0
		} else {
			ledger.CancellationFee = 0.0
		}
	}

	// Carpooling Discount: 20% discount on base and distance charges
	if isSharingEnabled {
		ledger.BaseFare = round2(ledger.BaseFare * 0.80)
		ledger.DistanceFare = round2(ledger.DistanceFare * 0.80)
	}

	// Stage 8: Total Fare
	total := ledger.BaseFare + ledger.DistanceFare + ledger.StopsFee + ledger.WaitingFee + ledger.CancellationFee
	ledger.TotalFare = round2(total)

	// Stage 9: Commission & Driver Payout
	ledger.CommissionRate = snap.DefaultCommissionPct
	if ledger.CommissionRate <= 0 {
		ledger.CommissionRate = 10.0 // Default 10%
	}

	// Match custom CommissionRule if available
	for _, cr := range snap.CommissionRules {
		if !cr.IsActive {
			continue
		}
		if cr.ServiceType == "ride" || cr.ServiceType == "" {
			if cr.Category != nil && *cr.Category == vehicleCategorySlug {
				ledger.CommissionRate = cr.Percentage
				ledger.CommissionFlat = cr.FlatFee
				break
			}
		}
	}

	// If driver is on Subscription OR in 14-day free trial -> 0% commission!
	if ledger.BillingModel == "subscription" || isDriverInTrial {
		ledger.CommissionAmount = 0.0
		ledger.DriverPayout = ledger.TotalFare
	} else {
		// Commission model: 10% (or rule rate)
		comm := (ledger.TotalFare * (ledger.CommissionRate / 100.0)) + ledger.CommissionFlat
		ledger.CommissionAmount = round2(comm)
		ledger.DriverPayout = round2(ledger.TotalFare - ledger.CommissionAmount)
	}

	return ledger
}

// CalculateFareEstimates provides total fares across all active categories
func CalculateFareEstimates(
	snap *config.PricingSnapshot,
	distanceKm float64,
	surgeMultiplier float64,
	numStops int,
	isSharingEnabled bool,
) map[string]float64 {
	estimates := make(map[string]float64)
	for _, cat := range snap.Categories {
		if !cat.IsActive {
			continue
		}
		ledger := ComputeFinalFare(
			snap,
			distanceKm,
			cat.Slug,
			nil, nil,
			0,
			"cash",
			numStops,
			&surgeMultiplier,
			isSharingEnabled,
			false,
			"subscription",
			false,
		)
		estimates[cat.Slug] = ledger.TotalFare
	}
	return estimates
}

// ComputeCourierFare calculates fare for courier delivery
func ComputeCourierFare(
	snap *config.PricingSnapshot,
	distanceKm float64,
	vehicleTypeID string,
	categoryID *string,
	weightTierID *string,
	surgeMultiplier float64,
	promoDiscount float64,
	driverBillingModel string,
	isDriverInTrial bool,
) CourierFareLedger {
	ledger := CourierFareLedger{
		BillingModel:    driverBillingModel,
		SurgeMultiplier: surgeMultiplier,
		DiscountAmount:  promoDiscount,
	}
	if ledger.BillingModel == "" {
		ledger.BillingModel = "subscription"
	}
	if ledger.SurgeMultiplier <= 0 {
		ledger.SurgeMultiplier = 1.0
	}

	// 1. Vehicle Type
	var vtype *config.DeliveryVehicleType
	for i := range snap.DeliveryVehicleTypes {
		if snap.DeliveryVehicleTypes[i].ID == vehicleTypeID {
			vtype = &snap.DeliveryVehicleTypes[i]
			break
		}
	}
	if vtype == nil && len(snap.DeliveryVehicleTypes) > 0 {
		vtype = &snap.DeliveryVehicleTypes[0]
	}
	if vtype != nil {
		ledger.BaseFare = vtype.BaseFare
		ledger.DistanceFare = round2(distanceKm * vtype.PerKmRate * ledger.SurgeMultiplier)
	}

	subTotal := ledger.BaseFare + ledger.DistanceFare

	// 2. Weight Tier Markup
	if weightTierID != nil {
		for _, wt := range snap.DeliveryWeightTiers {
			if wt.ID == *weightTierID && wt.MarkupPercentage > 0 {
				ledger.WeightMarkup = round2(subTotal * (wt.MarkupPercentage / 100.0))
				break
			}
		}
	}

	// 3. Category Markup
	if categoryID != nil {
		for _, cat := range snap.DeliveryCategories {
			if cat.ID == *categoryID && cat.MarkupPercentage > 0 {
				ledger.CategoryMarkup = round2(subTotal * (cat.MarkupPercentage / 100.0))
				break
			}
		}
	}

	totalBeforeDiscount := subTotal + ledger.WeightMarkup + ledger.CategoryMarkup
	total := math.Max(0.0, totalBeforeDiscount-ledger.DiscountAmount)
	ledger.TotalFare = round2(total)

	// Commission & Driver Payout
	ledger.CommissionRate = snap.DefaultCommissionPct
	if ledger.CommissionRate <= 0 {
		ledger.CommissionRate = 10.0
	}

	if ledger.BillingModel == "subscription" || isDriverInTrial {
		ledger.CommissionAmount = 0.0
		ledger.DriverPayout = ledger.TotalFare
	} else {
		comm := ledger.TotalFare * (ledger.CommissionRate / 100.0)
		ledger.CommissionAmount = round2(comm)
		ledger.DriverPayout = round2(ledger.TotalFare - ledger.CommissionAmount)
	}

	return ledger
}

func round2(val float64) float64 {
	return math.Round(val*100.0) / 100.0
}
