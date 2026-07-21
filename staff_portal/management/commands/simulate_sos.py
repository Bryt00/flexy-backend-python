"""
simulate_sos.py  —  FlexyRide SOS Pipeline Simulation
------------------------------------------------------
Fires 3 realistic SOS scenarios through the full channel-layer pipeline
so the staff portal receives live push alerts exactly as production would.

Usage:
    python manage.py simulate_sos              # fires all 3 with 4-second gaps
    python manage.py simulate_sos --scenario 1 # fire a specific scenario (1-3)
    python manage.py simulate_sos --delay 2    # custom delay between scenarios (seconds)
"""

import time
import uuid
from datetime import datetime, timezone as dt_tz

from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Accra / Koforidua area coordinates for realism
SCENARIOS = [
    {
        "label": "🆘  Scenario 1 — Rider manually triggered SOS",
        "data": {
            "incident_id": str(uuid.uuid4()),
            "ride_id":     str(uuid.uuid4()),
            "reporter_email": "rider@test.com",
            "type": "SOS",
            "description": "SOS Triggered — Passenger felt unsafe near Accra Mall interchange.",
            "location_lat": 5.6037,
            "location_lng": -0.1870,
        }
    },
    {
        "label": "🚨  Scenario 2 — Auto-detection: Driver route deviation",
        "data": {
            "incident_id": str(uuid.uuid4()),
            "ride_id":     str(uuid.uuid4()),
            "reporter_email": "System (Auto-detected)",
            "type": "SOS",
            "description": (
                "Automated Anomaly Detection: Driver is 4.2km from destination, "
                "exceeding expected bounds. Route deviation detected on Spintex Road trip."
            ),
            "location_lat": 5.6501,
            "location_lng": -0.1630,
        }
    },
    {
        "label": "⚠️   Scenario 3 — Auto-detection: Driver offline / stuck",
        "data": {
            "incident_id": str(uuid.uuid4()),
            "ride_id":     str(uuid.uuid4()),
            "reporter_email": "System (Auto-detected)",
            "type": "SOS",
            "description": (
                "Automated Anomaly Detection: Driver location has been stuck/offline "
                "for over 15 minutes on an active trip from Koforidua."
            ),
            "location_lat": 6.0939,
            "location_lng": -0.2609,
        }
    },
]


class Command(BaseCommand):
    help = "Simulate SOS alert scenarios through the live WebSocket pipeline"

    def add_arguments(self, parser):
        parser.add_argument(
            "--scenario",
            type=int,
            default=0,
            help="Fire a single scenario by number (1-3). Omit to fire all.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=4.0,
            help="Seconds between each scenario when firing all (default: 4).",
        )

    def handle(self, *args, **options):
        channel_layer = get_channel_layer()
        if not channel_layer:
            self.stderr.write(self.style.ERROR(
                "No channel layer configured. Make sure Redis is running on port 6380."
            ))
            return

        scenario_num = options["scenario"]
        delay = options["delay"]

        if scenario_num:
            if scenario_num < 1 or scenario_num > len(SCENARIOS):
                self.stderr.write(self.style.ERROR(f"Invalid scenario. Choose 1-{len(SCENARIOS)}."))
                return
            targets = [SCENARIOS[scenario_num - 1]]
        else:
            targets = SCENARIOS

        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}\n  FlexyRide SOS Simulation — {len(targets)} scenario(s)\n{'='*60}"
        ))

        for i, scenario in enumerate(targets):
            self.stdout.write(f"\n  [{i+1}/{len(targets)}] {scenario['label']}")

            payload = dict(scenario["data"])
            payload["created_at"] = timezone.now().isoformat()

            try:
                async_to_sync(channel_layer.group_send)(
                    "admin_alerts",
                    {
                        "type": "admin_alert",
                        "data": payload,
                    },
                )
                self.stdout.write(self.style.SUCCESS(
                    f"       ✓ Pushed to admin_alerts group\n"
                    f"         incident_id : {payload['incident_id']}\n"
                    f"         reporter    : {payload['reporter_email']}\n"
                    f"         location    : {payload['location_lat']}, {payload['location_lng']}"
                ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"       ✗ Failed: {e}"))

            if i < len(targets) - 1:
                self.stdout.write(f"\n  ⏱  Waiting {delay}s before next scenario...")
                time.sleep(delay)

        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}\n  Simulation complete. Check the staff portal for alerts.\n{'='*60}\n"
        ))
