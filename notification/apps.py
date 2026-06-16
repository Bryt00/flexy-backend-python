from django.apps import AppConfig
import os

class NotificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notification'

    def ready(self):
        import firebase_admin
        from firebase_admin import credentials
        from django.conf import settings
        
        # Avoid re-initializing if already done
        if not firebase_admin._apps:
            if hasattr(settings, 'FIREBASE_CREDENTIALS_PATH') and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
