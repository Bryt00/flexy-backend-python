from django.core.management.base import BaseCommand
from rides.engine_sync import sync_pricing_config_to_redis

class Command(BaseCommand):
    help = "Syncs pricing rules, vehicle categories, distance tiers, and delivery settings to Redis for flexy-engine"

    def handle(self, *args, **options):
        self.stdout.write("Syncing pricing configuration to Redis...")
        success = sync_pricing_config_to_redis()
        if success:
            self.stdout.write(self.style.SUCCESS("Successfully synced pricing config to Redis key 'engine:config:pricing'."))
        else:
            self.stdout.write(self.style.ERROR("Failed to sync pricing config to Redis."))
