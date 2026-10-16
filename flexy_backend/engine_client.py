import socket
import http.client
import json
import logging
import os
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class UnixHTTPConnection(http.client.HTTPConnection):
    """HTTP connection over a Unix domain socket using standard library."""
    def __init__(self, socket_path: str, timeout: float = 0.15):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


class EngineClient:
    """
    High-performance client to flexy-engine with automatic circuit breaker and fallback.
    """
    def __init__(self):
        self.socket_path = os.getenv("FLEXY_ENGINE_SOCKET", "/tmp/flexy_engine.sock")
        self.http_host = os.getenv("FLEXY_ENGINE_HOST", "127.0.0.1")
        self.http_port = int(os.getenv("FLEXY_ENGINE_PORT", "8091"))
        self.enabled = os.getenv("FLEXY_ENGINE_ENABLED", "true").lower() in ("true", "1", "yes")
        self.timeout = float(os.getenv("FLEXY_ENGINE_TIMEOUT", "0.20")) # 200ms default timeout
        
        # Circuit Breaker state
        self._failure_count = 0
        self._circuit_open_until = 0.0

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        if time.time() < self._circuit_open_until:
            return False
        return True

    def _record_success(self):
        self._failure_count = 0
        self._circuit_open_until = 0.0

    def _record_failure(self, err: Exception):
        self._failure_count += 1
        if self._failure_count >= 3:
            # Trip circuit for 10 seconds
            self._circuit_open_until = time.time() + 10.0
            logger.warning(f"FlexyEngine circuit breaker TRIPPED for 10s: {err}")
        else:
            logger.warning(f"FlexyEngine call failed ({self._failure_count}/3): {err}")

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if not self.is_available():
            return None

        body = json.dumps(payload).encode('utf-8') if payload is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}

        # 1. Try Unix domain socket first if file exists
        if self.socket_path and os.path.exists(self.socket_path):
            try:
                conn = UnixHTTPConnection(self.socket_path, timeout=self.timeout)
                conn.request(method, path, body=body, headers=headers)
                resp = conn.getresponse()
                resp_data = resp.read()
                conn.close()
                if resp.status == 200:
                    self._record_success()
                    return json.loads(resp_data.decode('utf-8'))
                else:
                    self._record_failure(Exception(f"HTTP {resp.status}: {resp_data.decode('utf-8')}"))
                    return None
            except Exception as e:
                self._record_failure(e)
                # Fall through to try TCP
                pass

        # 2. Try TCP localhost
        try:
            conn = http.client.HTTPConnection(self.http_host, self.http_port, timeout=self.timeout)
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            resp_data = resp.read()
            conn.close()
            if resp.status == 200:
                self._record_success()
                return json.loads(resp_data.decode('utf-8'))
            else:
                self._record_failure(Exception(f"HTTP {resp.status}: {resp_data.decode('utf-8')}"))
                return None
        except Exception as e:
            self._record_failure(e)
            return None

    def get_surge_multiplier(self, lat=None, lng=None, radius=5.0, duration_seconds=None, duration_in_traffic=None, weather_surge=1.0) -> Optional[float]:
        res = self._request("POST", "/v1/pricing/surge", {
            "lat": lat,
            "lng": lng,
            "radius_km": radius,
            "duration_seconds": duration_seconds,
            "duration_in_traffic_seconds": duration_in_traffic,
            "weather_surge": weather_surge,
        })
        if res and "surge_multiplier" in res:
            return float(res["surge_multiplier"])
        return None

    def calculate_fare_estimates(self, dist_km, duration_sec, lat=None, lng=None, num_stops=0, is_sharing=False, weather_surge=1.0, duration_in_traffic=None) -> Optional[Dict[str, Any]]:
        res = self._request("POST", "/v1/pricing/estimate", {
            "distance_km": dist_km,
            "duration_seconds": duration_sec,
            "duration_in_traffic_seconds": duration_in_traffic,
            "lat": lat,
            "lng": lng,
            "num_stops": num_stops,
            "is_sharing_enabled": is_sharing,
            "weather_surge": weather_surge,
        })
        return res

    def compute_final_fare(self, distance_km, category_slug, lat=None, lng=None, waiting_minutes=0, payment_method='cash', num_stops=0, surge_override=None, is_sharing=False, is_cancelled=False, driver_billing_model="subscription", is_trial=False) -> Optional[Dict[str, Any]]:
        res = self._request("POST", "/v1/pricing/final", {
            "distance_km": distance_km,
            "vehicle_category_slug": category_slug,
            "lat": lat,
            "lng": lng,
            "waiting_minutes": waiting_minutes,
            "payment_method": payment_method,
            "num_stops": num_stops,
            "surge_override": surge_override,
            "is_sharing_enabled": is_sharing,
            "is_cancelled": is_cancelled,
            "driver_billing_model": driver_billing_model,
            "is_driver_in_trial": is_trial,
        })
        return res

    def compute_courier_fare(self, distance_km, vehicle_type_id, category_id=None, weight_tier_id=None, surge_multiplier=1.0, promo_discount=0.0, driver_billing_model="subscription", is_trial=False) -> Optional[Dict[str, Any]]:
        res = self._request("POST", "/v1/pricing/courier", {
            "distance_km": distance_km,
            "vehicle_type_id": str(vehicle_type_id) if vehicle_type_id else "",
            "category_id": str(category_id) if category_id else None,
            "weight_tier_id": str(weight_tier_id) if weight_tier_id else None,
            "surge_multiplier": surge_multiplier,
            "promo_discount": promo_discount,
            "driver_billing_model": driver_billing_model,
            "is_driver_in_trial": is_trial,
        })
        return res

    def update_driver_location(self, driver_id: str, lat: float, lng: float, user_id: Optional[str] = None) -> bool:
        res = self._request("POST", "/v1/location/update", {
            "driver_id": str(driver_id),
            "user_id": str(user_id) if user_id else "",
            "lat": lat,
            "lng": lng,
        })
        return res is not None and res.get("status") == "ok"

    def find_nearby_drivers(self, pickup_lat: float, pickup_lng: float, attempt_count: int = 0, excluded_driver_ids=None, distance_history=None) -> Optional[Dict[str, Any]]:
        payload = {
            "pickup_lat": float(pickup_lat),
            "pickup_lng": float(pickup_lng),
            "attempt_count": int(attempt_count),
            "excluded_driver_ids": [str(x) for x in (excluded_driver_ids or [])],
            "distance_history": distance_history or {},
        }
        return self._request("POST", "/v1/tracking/nearby-drivers", payload)

    def evaluate_pooling(self, active_candidates: list, new_ride: dict) -> Optional[Dict[str, Any]]:
        payload = {
            "active_candidates": active_candidates,
            "new_ride": new_ride,
        }
        return self._request("POST", "/v1/pooling/match", payload)


# Singleton instance
engine_client = EngineClient()
