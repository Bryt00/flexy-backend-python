import json
import time
import hmac
import hashlib
import urllib.request
import urllib.error
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WebhookService:
    """
    Outbound webhook dispatcher for external integrations.
    Signs payloads using HMAC-SHA256 with timestamp headers (anti-replay).
    """

    @classmethod
    def generate_signature(cls, payload_bytes: bytes, secret: str, timestamp: int) -> str:
        """
        Creates an HMAC-SHA256 signature for the given payload and timestamp.
        Format: v1=<hex_signature>
        """
        signed_payload = f"t={timestamp}.".encode('utf-8') + payload_bytes
        signature = hmac.new(secret.encode('utf-8'), signed_payload, hashlib.sha256).hexdigest()
        return f"t={timestamp},v1={signature}"

    @classmethod
    def send_event(cls, webhook_url: str, secret: str, event_type: str, data: Dict[str, Any], timeout: int = 5) -> Dict[str, Any]:
        """
        Sends an HTTP POST webhook notification to the given URL.
        Returns a dict with success, status_code, response_body, and latency_ms.
        """
        if not webhook_url:
            return {"success": False, "error": "No webhook URL configured"}

        payload = {
            "event": event_type,
            "timestamp": int(time.time()),
            "data": data
        }
        payload_bytes = json.dumps(payload, default=str).encode('utf-8')
        timestamp = int(time.time())
        signature_header = cls.generate_signature(payload_bytes, secret or "", timestamp)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "FlexyRide-Webhook/1.0",
            "X-Flexy-Event": event_type,
            "X-Flexy-Signature": signature_header
        }

        req = urllib.request.Request(webhook_url, data=payload_bytes, headers=headers, method='POST')
        start_time = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                latency_ms = int((time.time() - start_time) * 1000)
                body = response.read().decode('utf-8', errors='ignore')
                return {
                    "success": 200 <= response.status < 300,
                    "status_code": response.status,
                    "latency_ms": latency_ms,
                    "body": body[:500]
                }
        except urllib.error.HTTPError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "status_code": e.code,
                "latency_ms": latency_ms,
                "error": f"HTTP {e.code}: {e.reason}"
            }
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "status_code": None,
                "latency_ms": latency_ms,
                "error": str(e)
            }

