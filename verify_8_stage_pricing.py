import os
import django
import math
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from rides.utils import FareCalculator
from core_settings.models import VehicleCategory, DistanceTier

def verify_math():
    print("--- Verifying 8-Stage Pricing Logic ---")
    
    # Test Case: 10km Go Ride in Peak Hour (1.3x Surge)
    # Expected logic:
    # Base: 18.0
    # Tier 1 (5km @ 6.0): 30.0
    # Tier 2 (5km @ 5.0): 25.0
    # Categorized & Surged Distance Charge: (30 + 25) * 1.0 (multiplier) * 1.3 (surge) = 55 * 1.3 = 71.5
    # Overall total expected: 18.0 + 71.5 = 89.5 GHS
    
    # Mock Peak Time
    peak_time = datetime.strptime("07:00", "%H:%M").time()
    surge = FareCalculator.get_surge_multiplier(peak_time)
    print(f"Surge Multiplier at 07:00: {surge} (Expected: 1.3)")
    
    # Manually trigger calculation for verification
    ledger = FareCalculator.compute_final_fare(
        distance_km=10.0,
        vehicle_category_slug='go',
    )
    
    # Note: Ledger logic in compute_final_fare uses datetime.now() for surge.
    # To test specifically with 1.3, we'll assume it's peak time or manually check the math.
    
    print("\n[SCENARIO 1: 10km Go Ride]")
    print(f"Base Fare: {ledger['base_fare']} GHS")
    print(f"Distance Fare (including Surge {ledger['surge_multiplier']}x): {ledger['distance_fare']} GHS")
    print(f"Total Fare: {ledger['total_fare']} GHS")
    
    # Test Case: Waiting Fee
    # Expected for 10 mins (5 paid): 2.0 * (1.002)^4 = 2.016... rounds to 2.02
    wait_10 = FareCalculator.calculate_waiting_fee(10)
    print(f"\n[SCENARIO 2: 10 Min Waiting]")
    print(f"Waiting Fee for 10 mins: {wait_10} GHS (Expected: ~2.02)")
    
    # Test Case: Cancellation
    cancel_card = FareCalculator.compute_final_fare(0, 'go', is_cancelled=True, payment_method='card')
    print(f"\n[SCENARIO 3: Card Cancellation]")
    print(f"Cancellation Fee: {cancel_card['cancellation_fee']} GHS (Expected: 8.0)")
    
    # Test Case: Payout
    print(f"\n[SCENARIO 4: Payout Assignment]")
    print(f"Driver Payout: {ledger['driver_payout']} GHS (Expected: 100% of {ledger['total_fare']})")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_math()
