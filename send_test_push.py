import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

import firebase_admin
from firebase_admin import messaging
from core_auth.models import User
from notification.models import FCMDevice

email = "kabrytlex2468@gmail.com"

# 1. Verify Firebase is initialized
if not firebase_admin._apps:
    print("❌ Firebase Admin SDK is NOT initialized!")
    print("   Check FIREBASE_CREDENTIALS_PATH in .env")
    sys.exit(1)
else:
    print("✅ Firebase Admin SDK is initialized")

# 2. Find user
try:
    user = User.objects.get(email=email)
    print(f"✅ Found user: {user.email} (id: {user.id})")
except User.DoesNotExist:
    print(f"❌ User with email {email} does not exist.")
    sys.exit(1)

# 3. Check FCM devices
devices = FCMDevice.objects.filter(user=user)
if not devices.exists():
    print("❌ No FCM devices registered for this user!")
    sys.exit(1)

for d in devices:
    token_preview = d.registration_id[:20] + "..." if len(d.registration_id) > 20 else d.registration_id
    print(f"✅ Found device: {token_preview} (updated: {d.updated_at})")

# 4. Send push DIRECTLY (not via thread) so we see the real result
tokens = [d.registration_id for d in devices]
payload_data = {
    'title': 'Test Push Notification',
    'body': 'Hello! This is a test push from the FlexyRide backend.',
    # To test with alarm sound, set: 'android_channel_id': 'high_priority_rides'
    # For a quiet in-app toast, omit android_channel_id
}

fcm_message = messaging.MulticastMessage(
    data=payload_data,
    tokens=tokens,
)

try:
    response = messaging.send_each_for_multicast(fcm_message)
    print(f"\n📊 FCM Response:")
    print(f"   Success: {response.success_count}")
    print(f"   Failure: {response.failure_count}")
    for idx, resp in enumerate(response.responses):
        if resp.success:
            print(f"   ✅ Token {idx}: message_id={resp.message_id}")
        else:
            print(f"   ❌ Token {idx}: {resp.exception}")
except Exception as e:
    print(f"❌ FCM send failed: {e}")
    import traceback
    traceback.print_exc()
