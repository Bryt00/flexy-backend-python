package config

import (
	"context"
	"encoding/json"
	"log/slog"
	"sync"
	"sync/atomic"

	"github.com/redis/go-redis/v9"
)

// VehicleCategory mirrors core_settings.models.VehicleCategory
type VehicleCategory struct {
	Slug               string  `json:"slug"`
	Name               string  `json:"name"`
	BaseFare           float64 `json:"base_fare"`
	Multiplier         float64 `json:"multiplier"`
	IsActive           bool    `json:"is_active"`
	IsPassengerAllowed bool    `json:"is_passenger_allowed"`
}

// DistanceTier mirrors core_settings.models.DistanceTier
type DistanceTier struct {
	MinKm     float64 `json:"min_km"`
	MaxKm     float64 `json:"max_km"`
	RatePerKm float64 `json:"rate_per_km"`
	IsActive  bool    `json:"is_active"`
}

// PricingRule mirrors core_settings.models.PricingRule
type PricingRule struct {
	ID                 string   `json:"id"`
	CityID             *string  `json:"city_id"`
	CityName           *string  `json:"city_name"`
	CityLat            *float64 `json:"city_lat"`
	CityLng            *float64 `json:"city_lng"`
	CityIsActive       bool     `json:"city_is_active"`
	BaseFare           float64  `json:"base_fare"`
	PerKmRate          float64  `json:"per_km_rate"`
	SurgeMultiplier    float64  `json:"surge_multiplier"`
	EnableWeatherSurge bool     `json:"enable_weather_surge"`
	MaxWeatherSurge    float64  `json:"max_weather_surge"`
	EnableTrafficSurge bool     `json:"enable_traffic_surge"`
	MaxTrafficSurge    float64  `json:"max_traffic_surge"`
	IsActive           bool     `json:"is_active"`
}

// DeliveryCategory mirrors core_settings.models.DeliveryCategory
type DeliveryCategory struct {
	ID               string  `json:"id"`
	Name             string  `json:"name"`
	MarkupPercentage float64 `json:"markup_percentage"`
	IsActive         bool    `json:"is_active"`
}

// DeliveryWeightTier mirrors core_settings.models.DeliveryWeightTier
type DeliveryWeightTier struct {
	ID               string  `json:"id"`
	Name             string  `json:"name"`
	MinWeightKg      float64 `json:"min_weight_kg"`
	MaxWeightKg      float64 `json:"max_weight_kg"`
	MarkupPercentage float64 `json:"markup_percentage"`
	IsActive         bool    `json:"is_active"`
}

// DeliveryVehicleType mirrors core_settings.models.DeliveryVehicleType
type DeliveryVehicleType struct {
	ID        string  `json:"id"`
	Name      string  `json:"name"`
	BaseFare  float64 `json:"base_fare"`
	PerKmRate float64 `json:"per_km_rate"`
	IsActive  bool    `json:"is_active"`
}

// CommissionRule mirrors core_settings.models.CommissionRule
type CommissionRule struct {
	ID          string   `json:"id"`
	CityID      *string  `json:"city_id"`
	Category    *string  `json:"category"`
	ServiceType string   `json:"service_type"` // "ride" or "delivery"
	Percentage  float64  `json:"percentage"`   // default 10.0
	FlatFee     float64  `json:"flat_fee"`
	MinFee      float64  `json:"min_fee"`
	MaxFee      float64  `json:"max_fee"`
	IsActive    bool     `json:"is_active"`
}

// PricingSnapshot is the complete configuration snapshot synced from Django
type PricingSnapshot struct {
	Categories           []VehicleCategory     `json:"categories"`
	DistanceTiers        []DistanceTier        `json:"distance_tiers"`
	PricingRules         []PricingRule         `json:"pricing_rules"`
	DeliveryCategories   []DeliveryCategory    `json:"delivery_categories"`
	DeliveryWeightTiers  []DeliveryWeightTier  `json:"delivery_weight_tiers"`
	DeliveryVehicleTypes []DeliveryVehicleType `json:"delivery_vehicle_types"`
	CommissionRules      []CommissionRule      `json:"commission_rules"`
	DefaultCommissionPct float64               `json:"default_commission_pct"` // 10.0
}

// Store holds the atomic in-memory copy of PricingSnapshot
type Store struct {
	current atomic.Pointer[PricingSnapshot]
	mu      sync.RWMutex
	rdb     *redis.Client
}

const RedisConfigKey = "engine:config:pricing"

// NewStore initializes a Store with default fallback values
func NewStore(rdb *redis.Client) *Store {
	s := &Store{rdb: rdb}
	defaultSnap := defaultSnapshot()
	s.current.Store(&defaultSnap)
	return s
}

// Get returns the current active snapshot
func (s *Store) Get() *PricingSnapshot {
	return s.current.Load()
}

// Update sets the snapshot atomically
func (s *Store) Update(snap *PricingSnapshot) {
	s.current.Store(snap)
}

// SyncFromRedis reads the JSON snapshot from Redis and updates the memory store
func (s *Store) SyncFromRedis(ctx context.Context) error {
	if s.rdb == nil {
		return nil
	}
	val, err := s.rdb.Get(ctx, RedisConfigKey).Result()
	if err != nil {
		if err == redis.Nil {
			slog.Debug("Redis config snapshot key not found, keeping defaults")
			return nil
		}
		return err
	}

	var snap PricingSnapshot
	if err := json.Unmarshal([]byte(val), &snap); err != nil {
		return err
	}

	s.Update(&snap)
	slog.Info("Successfully synced pricing config snapshot from Redis",
		"categories", len(snap.Categories),
		"tiers", len(snap.DistanceTiers),
		"rules", len(snap.PricingRules),
	)
	return nil
}

// defaultSnapshot provides default system constants if Redis has not been seeded yet
func defaultSnapshot() PricingSnapshot {
	return PricingSnapshot{
		DefaultCommissionPct: 10.0,
		Categories: []VehicleCategory{
			{Slug: "go", Name: "Flexy Go", BaseFare: 18.0, Multiplier: 1.0, IsActive: true, IsPassengerAllowed: true},
			{Slug: "comfort", Name: "Flexy Comfort", BaseFare: 22.0, Multiplier: 1.25, IsActive: true, IsPassengerAllowed: true},
			{Slug: "xl", Name: "Flexy XL", BaseFare: 26.0, Multiplier: 1.5, IsActive: true, IsPassengerAllowed: true},
			{Slug: "exec", Name: "Flexy Exec", BaseFare: 30.0, Multiplier: 2.0, IsActive: true, IsPassengerAllowed: true},
			{Slug: "pragya", Name: "Flexy Pragya", BaseFare: 10.0, Multiplier: 0.6, IsActive: true, IsPassengerAllowed: true},
		},
		DistanceTiers: []DistanceTier{
			{MinKm: 0.0, MaxKm: 5.0, RatePerKm: 6.0, IsActive: true},
			{MinKm: 5.0, MaxKm: 11.0, RatePerKm: 5.0, IsActive: true},
			{MinKm: 11.0, MaxKm: 17.0, RatePerKm: 4.5, IsActive: true},
			{MinKm: 17.0, MaxKm: 9999.0, RatePerKm: 4.0, IsActive: true},
		},
		PricingRules: []PricingRule{
			{
				ID:                 "default_global_rule",
				BaseFare:           0.0,
				PerKmRate:          0.0,
				SurgeMultiplier:    1.0,
				EnableWeatherSurge: true,
				MaxWeatherSurge:    1.5,
				EnableTrafficSurge: true,
				MaxTrafficSurge:    1.5,
				IsActive:           true,
			},
		},
		DeliveryVehicleTypes: []DeliveryVehicleType{
			{ID: "bike", Name: "Delivery Motorbike", BaseFare: 12.0, PerKmRate: 3.5, IsActive: true},
			{ID: "car", Name: "Delivery Car", BaseFare: 18.0, PerKmRate: 4.5, IsActive: true},
			{ID: "van", Name: "Delivery Van", BaseFare: 35.0, PerKmRate: 6.5, IsActive: true},
		},
	}
}
