import requests
import logging
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WeatherService:
    # Class-level in-memory fallback cache to bypass Redis/network overhead
    _mem_cache = {}

    @staticmethod
    def get_weather_surge(lat, lng):
        """
        Queries Open-Meteo for the current weather at (lat, lng).
        Uses a Grid-Based Redis Cache + In-Memory Fallback Cache.
        Returns a weather multiplier (e.g. 1.2 for rain, 1.5 for thunderstorm).
        """
        if lat is None or lng is None:
            return 1.0

        # Round to 1 decimal place for 11km x 11km grid caching
        grid_lat = round(float(lat), 1)
        grid_lng = round(float(lng), 1)
        cache_key = f"{grid_lat}_{grid_lng}"
        redis_key = f"weather_surge_grid_{cache_key}"

        now = datetime.now()

        # 1. Check in-memory fallback cache first (extremely fast)
        if cache_key in WeatherService._mem_cache:
            val, expiry = WeatherService._mem_cache[cache_key]
            if now < expiry:
                logger.info(f"Weather In-Memory Cache Hit for grid [{grid_lat}, {grid_lng}]: {val}x")
                return val

        # 2. Check Django cache (Redis) with try-except for tolerance
        try:
            cached_surge = cache.get(redis_key)
            if cached_surge is not None:
                logger.info(f"Weather Redis Cache Hit for grid [{grid_lat}, {grid_lng}]: {cached_surge}x")
                val = float(cached_surge)
                WeatherService._mem_cache[cache_key] = (val, now + timedelta(minutes=15))
                return val
        except Exception as e:
            logger.warning(f"Weather Cache service unavailable: {e}")

        # 3. Fetch from Open-Meteo if not cached
        surge = 1.0
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": grid_lat,
                "longitude": grid_lng,
                "current": "weather_code"
            }
            # Short timeout to prevent locking threads on external network delays
            response = requests.get(url, params=params, timeout=2)
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

        # 4. Cache the calculated surge for 15 minutes (900 seconds) in Django cache and In-Memory
        try:
            cache.set(redis_key, surge, timeout=900)
        except Exception as e:
            logger.warning(f"Failed to write weather to Redis cache: {e}")

        WeatherService._mem_cache[cache_key] = (surge, now + timedelta(minutes=15))
        return surge
