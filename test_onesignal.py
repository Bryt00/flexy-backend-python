import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flexy_backend.settings')
django.setup()

from notification.providers.onesignal import OneSignalProvider

provider = OneSignalProvider()
success = provider.send_push(user_id="0", title="Test from Django", message="This is a test push notification via the new Abstraction Layer!")

if success:
    print("SUCCESS: OneSignal API accepted the request.")
else:
    print("FAILED: OneSignal API rejected the request. Check your logs/keys.")
