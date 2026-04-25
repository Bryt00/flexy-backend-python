import requests
import datetime
import json

def debug_schedule():
    url = "http://127.0.0.1:8000/v1/rides/schedule/"
    headers = {
        "Authorization": "Token 338c227aeef1968be8ad27702810a9ba1a067a99", # Using the token from the other script
        "Content-Type": "application/json"
    }
    
    # Try to emulate the Flutter payload as much as possible
    now = datetime.datetime.now(datetime.timezone.utc)
    scheduled_for = (now + datetime.timedelta(hours=1)).isoformat()
    
    payload = {
        "id": "",
        "rider_id": "1990fa2a-4905-4c41-9507-5e46d144aadf",
        "driver_id": None,
        "pickup_lat": 6.1003337,
        "pickup_lng": -0.2614576,
        "dropoff_lat": 6.0663414,
        "dropoff_lng": -0.2671477,
        "pickup_address": "4P2Q+4C Koforidua, Ghana",
        "dropoff_address": "Nasco Hotel",
        "fare": 0.0,
        "distance": 0.0,
        "status": "scheduled",
        "preferred_vehicle_type": "standard",
        "type": "standard",
        "is_scheduled": True,
        "scheduled_for": scheduled_for,
        "stops": [],
        "payment_method": "cash",
        "quiet_ride_requested": False
    }
    
    print(f"POSTing to {url}...")
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response (text): {response.text}")

if __name__ == "__main__":
    debug_schedule()
