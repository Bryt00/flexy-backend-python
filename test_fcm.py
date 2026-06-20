import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from core_auth.models import User
from notification.utils import send_notification
from notification.models import FCMDevice

def main():
    email = input("Enter the user email to send test notification to: ").strip()
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        print(f"Error: User with email '{email}' does not exist.")
        return

    devices = FCMDevice.objects.filter(user=user)
    if not devices.exists():
        print(f"Warning: User '{email}' has no registered FCM devices in the database.")
        print("Please log in on the mobile app to register a device token first.")
    else:
        print(f"Found {devices.count()} registered device(s) for user '{email}':")
        for dev in devices:
            print(f" - Device ID: {dev.device_id} | Token: {dev.registration_id[:20]}...")

    title = "Test Push Notification"
    body = "Hello from FlexyRide! If you receive this, FCM pushes are fully working."

    print("\nSending test notification via background task/thread...")
    try:
        notification = send_notification(user, title, body, type='PUSH')
        print(f"Notification successfully queued in DB (ID: {notification.id}).")
        print("Check the server/celery logs to verify the Firebase response.")
    except Exception as e:
        print(f"Error executing notification dispatch: {e}")

if __name__ == '__main__':
    main()
