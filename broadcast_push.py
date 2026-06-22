import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

import firebase_admin
from firebase_admin import messaging
from notification.models import FCMDevice

# 1. Verify Firebase is initialized
if not firebase_admin._apps:
    print("❌ Firebase Admin SDK is NOT initialized!")
    sys.exit(1)

# 2. Check FCM devices
devices = FCMDevice.objects.all()
if not devices.exists():
    print("❌ No FCM devices registered!")
    sys.exit(1)

tokens = list(set([d.registration_id for d in devices]))
print(f"✅ Found {len(tokens)} unique device tokens")

payload_data = {
    'title': 'Hello From Flexy',
    'body': 'Hello From Flexy',
    'type': 'general_update'
}

print(f"Sending push to {len(tokens)} devices...")

success_total = 0
failure_total = 0

try:
    for i in range(0, len(tokens), 500):
        batch = tokens[i:i+500]
        fcm_message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title='Hello From Flexy',
                body='Hello From Flexy'
            ),
            data=payload_data,
            tokens=batch,
        )
        response = messaging.send_each_for_multicast(fcm_message)
        success_total += response.success_count
        failure_total += response.failure_count
        print(f"Batch {i//500 + 1}: Success: {response.success_count}, Failure: {response.failure_count}")
except Exception as e:
    print(f"❌ FCM send failed: {e}")

print(f"\n📊 Broadcast Complete: {success_total} successful, {failure_total} failed.")
