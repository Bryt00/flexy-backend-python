import requests
import json

# Replace with the user's base URL/IP if known, or localhost
BASE_URL = "http://127.0.0.1:8000"

# Assuming we have a token or can use a mock user if testing locally
# But I'll just try to guess a valid payload based on the frontend
payload = {
    "pickup_lat": 6.0391416,
    "pickup_lng": -0.2782184,
    "dropoff_lat": 6.0663414,
    "dropoff_lng": -0.2671477,
    "pickup_address": "Ahodwo Christian Village",
    "dropoff_address": "Nasco Hotel",
    "fare": 50.0,
    "distance": 5.2,
    "status": "pending",
    "type": "standard"
}

print(f"Testing POST {BASE_URL}/v1/rides/...")
try:
    # We might need an auth token. I'll check if I can get one from the db or a test user.
    # For now, let's just see if we get a 401 (Auth) or 400 (Validation)
    response = requests.post(f"{BASE_URL}/v1/rides/", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
