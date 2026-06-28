import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class GoogleMapsService:
    @staticmethod
    def get_trip_metrics(origin_lat, origin_lng, dest_lat, dest_lng, waypoints=None):
        """
        Fetches distance and duration. For multi-stop routes, uses Directions API to sum up legs.
        Returns a tuple: (distance_km, duration_seconds, duration_in_traffic_seconds)
        """
        from django.core.cache import cache
        
        # Round coordinates to 3 decimal places (approx. 110m accuracy) for caching
        wp_part = ""
        if waypoints:
            wp_part = "_" + "_".join([
                f"{round(float(w.get('lat') or w.get('latitude') or 0), 3)}_{round(float(w.get('lng') or w.get('longitude') or 0), 3)}" 
                for w in waypoints
            ])
            
        cache_key = f"trip_metrics_{round(float(origin_lat), 3)}_{round(float(origin_lng), 3)}_{round(float(dest_lat), 3)}_{round(float(dest_lng), 3)}{wp_part}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        
        if not api_key:
            logger.warning("Google Maps API Key not configured. Using fallback estimation.")
            fallback_res = GoogleMapsService._get_fallback_metrics(origin_lat, origin_lng, dest_lat, dest_lng)
            cache.set(cache_key, fallback_res, timeout=900)
            return fallback_res

        # If waypoints exist, we must use Directions API to get total route metrics
        if waypoints and len(waypoints) > 0:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            # Format: 'lat1,lng1|lat2,lng2'
            waypoints_str = "|".join([f"{w.get('lat') or w.get('latitude')},{w.get('lng') or w.get('longitude')}" for w in waypoints])
            params = {
                'origin': f"{origin_lat},{origin_lng}",
                'destination': f"{dest_lat},{dest_lng}",
                'waypoints': waypoints_str,
                'key': api_key,
                'mode': 'driving',
                'departure_time': 'now'
            }
            
            try:
                response = requests.get(url, params=params, timeout=5)
                data = response.json()
                
                if data['status'] == 'OK':
                    route = data['routes'][0]
                    total_distance_m = 0
                    total_duration_s = 0
                    total_traffic_s = 0
                    for leg in route['legs']:
                        total_distance_m += leg['distance']['value']
                        total_duration_s += leg['duration']['value']
                        if 'duration_in_traffic' in leg:
                            total_traffic_s += leg['duration_in_traffic']['value']
                        else:
                            total_traffic_s += leg['duration']['value']
                    
                    result = (total_distance_m / 1000.0, total_duration_s, total_traffic_s)
                    cache.set(cache_key, result, timeout=900)
                    return result
                else:
                    logger.error(f"Directions API Error: {data.get('status')}")
            except Exception as e:
                logger.error(f"Directions API Exception: {e}")
            
            fallback_res = GoogleMapsService._get_fallback_metrics(origin_lat, origin_lng, dest_lat, dest_lng)
            cache.set(cache_key, fallback_res, timeout=900)
            return fallback_res

        # Simple point-to-point can still use Distance Matrix
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            'origins': f"{origin_lat},{origin_lng}",
            'destinations': f"{dest_lat},{dest_lng}",
            'key': api_key,
            'mode': 'driving',
            'departure_time': 'now'
        }

        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()

            if data['status'] == 'OK':
                element = data['rows'][0]['elements'][0]
                if element['status'] == 'OK':
                    distance_km = element['distance']['value'] / 1000.0
                    duration_seconds = element['duration']['value']
                    duration_in_traffic = duration_seconds
                    if 'duration_in_traffic' in element:
                        duration_in_traffic = element['duration_in_traffic']['value']
                    result = (distance_km, duration_seconds, duration_in_traffic)
                    cache.set(cache_key, result, timeout=900)
                    return result
                else:
                    logger.error(f"Google Maps Element Error: {element['status']}")
            else:
                logger.error(f"Google Maps API Error: {data.get('error_message', data['status'])}")
        except Exception as e:
            logger.error(f"Google Maps Request Exception: {str(e)}")

        fallback_res = GoogleMapsService._get_fallback_metrics(origin_lat, origin_lng, dest_lat, dest_lng)
        cache.set(cache_key, fallback_res, timeout=900)
        return fallback_res

    @staticmethod
    def _get_fallback_metrics(lat1, lng1, lat2, lng2):
        """
        Haversine fallback for distance calculation.
        """
        import math
        
        # Radius of the Earth in km
        R = 6371.0

        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        
        # 1.3x multiplier for road distance approximation
        distance_km = distance * 1.3
        
        # Assume average city speed of 30 km/h (0.5 km/min)
        duration_seconds = (distance_km / 30.0) * 3600
        
        return round(distance_km, 2), int(duration_seconds), int(duration_seconds)
