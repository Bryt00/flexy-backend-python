package geo

import (
	"math"
)

const earthRadiusMeters = 6371000.0 // Mean radius of the Earth in meters

// HaversineDistance calculates the great-circle distance between two points in meters.
// It directly mirrors GeospatialUtils.calculate_haversine_distance in Python.
func HaversineDistance(lat1, lon1, lat2, lon2 float64) float64 {
	ph1 := lat1 * math.Pi / 180.0
	ph2 := lat2 * math.Pi / 180.0
	dPh := (lat2 - lat1) * math.Pi / 180.0
	dLambda := (lon2 - lon1) * math.Pi / 180.0

	a := math.Sin(dPh/2.0)*math.Sin(dPh/2.0) +
		math.Cos(ph1)*math.Cos(ph2)*math.Sin(dLambda/2.0)*math.Sin(dLambda/2.0)
	c := 2.0 * math.Atan2(math.Sqrt(a), math.Sqrt(1.0-a))

	return earthRadiusMeters * c
}

// HaversineKm returns the distance in kilometers.
func HaversineKm(lat1, lon1, lat2, lon2 float64) float64 {
	return HaversineDistance(lat1, lon1, lat2, lon2) / 1000.0
}
