from django.apps import AppConfig


class RidesConfig(AppConfig):
    name = 'rides'

    def ready(self):
        import rides.signals
        
        # Trigger the headless 10-second heatmap pulse loop for Admins
        try:
            import sys
            import os
            # Avoid triggering during migrations or management commands other than dev server
            if 'runserver' in sys.argv or 'daphne' in sys.argv[0]:
                from .tasks import broadcast_heatmap_snapshot
                import threading
                # Run delay() in a background thread to avoid blocking server startup if Redis/RabbitMQ is unreachable
                threading.Thread(target=lambda: _safe_delay(broadcast_heatmap_snapshot)).start()
        except Exception:
            pass

def _safe_delay(task):
    try:
        task.delay()
    except Exception:
        pass
