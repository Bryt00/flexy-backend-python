import requests
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class WeatherService:
    @staticmethod
    def get_weather_surge(lat, lng):
        """
        Queries Open-Meteo for the current weather at (lat, lng).
        Uses a Grid-Based Redis Cache (rounded to 1 decimal place = ~11km grid)
        Returns a weather multiplier (e.g. 1.2 for rain, 1.5 for thunderstorm).
        """
        if lat is None or lng is None:
            return 1.0

        # Round to 1 decimal place for 11km x 11km grid caching
        grid_lat = round(float(lat), 1)
        grid_lng = round(float(lng), 1)
        cache_key = f"weather_surge_grid_{grid_lat}_{grid_lng}"

        # 1. Check Redis Cache
        cached_surge = cache.get(cache_key)
        if cached_surge is not None:
            logger.info(f"Weather Cache Hit for grid [{grid_lat}, {grid_lng}]: {cached_surge}x")
            return float(cached_surge)

        # 2. Fetch from Open-Meteo if not cached
        surge = 1.0
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": grid_lat,
                "longitude": grid_lng,
                "current": "weather_code"
            }
            response = requests.get(url, params=params, timeout=5)
            data = response.json()

            if "current" in data and "weather_code" in data["current"]:
                code = data["current"]["weather_code"]
                
                # WMO Weather interpretation codes
                # 51-67: Drizzle and Rain
                # 71-77: Snow fall
                # 80-82: Rain showers
                # 85-86: Snow showers
                # 95, 96, 99: Thunderstorm
                
                if code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
                    surge = 1.2
                    logger.info(f"Open-Meteo Detects Rain (Code {code}) at [{grid_lat}, {grid_lng}] -> Surge 1.2x")
                elif code in [71, 73, 75, 77, 85, 86, 95, 96, 99]:
                    surge = 1.5
                    logger.info(f"Open-Meteo Detects Snow/Storm (Code {code}) at [{grid_lat}, {grid_lng}] -> Surge 1.5x")
                else:
                    logger.info(f"Open-Meteo Detects Clear Weather (Code {code}) at [{grid_lat}, {grid_lng}] -> Surge 1.0x")
            else:
                logger.warning(f"Open-Meteo Unexpected Response: {data}")

        except Exception as e:
            logger.error(f"WeatherService API Exception: {e}")

        # 3. Cache the calculated surge for 15 minutes (900 seconds)
        cache.set(cache_key, surge, timeout=900)
        return surge
