import math
import logging
from rides.models import Ride, Incident
from django.utils import timezone

logger = logging.getLogger(__name__)

class SafetyService:
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Haversine formula to calculate distance in km."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def _push_incident_to_staff(incident):
        """Push a newly created incident to the admin_alerts WebSocket group."""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            if not channel_layer:
                return
            async_to_sync(channel_layer.group_send)(
                'admin_alerts',
                {
                    'type': 'admin_alert',
                    'data': {
                        'incident_id': str(incident.id),
                        'ride_id': str(incident.ride.id) if incident.ride else None,
                        'reporter_email': incident.reporter.email if incident.reporter else 'System (Auto-detected)',
                        'type': incident.type,
                        'description': incident.description,
                        'location_lat': incident.location_lat,
                        'location_lng': incident.location_lng,
                        'created_at': incident.created_at.isoformat(),
                    }
                }
            )
            logger.info(f"SafetyService: Pushed incident {incident.id} to admin_alerts group.")
        except Exception as e:
            logger.error(f"SafetyService: Failed to push incident to staff WS: {e}")

    @classmethod
    def check_ride_anomaly(cls, ride_id):
        """
        Anomaly detection: flags driver stuck/offline for 15+ mins or
        significantly deviating from the expected route.
        Creates an Incident and pushes it live to connected staff via WebSocket.
        """
        try:
            ride = Ride.objects.get(id=ride_id)
            if ride.status != 'in_progress' or not ride.driver:
                return False

            # Get driver's latest location from profile
            profile = ride.driver.profile
            curr_lat = profile.last_lat
            curr_lng = profile.last_lng

            if not curr_lat or not curr_lng:
                return False

            # 1. Check distance to destination
            dist_to_dest = cls.calculate_distance(curr_lat, curr_lng, ride.dropoff_lat, ride.dropoff_lng)

            # 2. Check if driver is "stuck" or disconnected (no location update in 15 mins)
            if profile.last_location_update:
                time_since_update = (timezone.now() - profile.last_location_update).total_seconds()
                if time_since_update > 900:  # 15 minutes
                    logger.warning(f"Safety: Ride {ride_id} anomaly — driver stuck/offline for {time_since_update:.0f}s.")
                    incident, created = Incident.objects.get_or_create(
                        ride=ride,
                        reporter=ride.rider,
                        type='SOS',
                        status='ACTIVE',
                        description=f"Automated Anomaly Detection: Driver location has been stuck/offline for over 15 minutes."
                    )
                    if created:
                        cls._push_incident_to_staff(incident)
                    return True

            # 3. Route deviation check — driver >50% further from dest than expected distance
            if dist_to_dest > ride.distance * 1.5 and dist_to_dest > 2.0:
                logger.warning(f"Safety: Ride {ride_id} anomaly — {dist_to_dest:.1f}km from destination.")
                incident, created = Incident.objects.get_or_create(
                    ride=ride,
                    reporter=ride.rider,
                    type='SOS',
                    status='ACTIVE',
                    description=f"Automated Anomaly Detection: Driver is {dist_to_dest:.1f}km from destination, exceeding expected bounds."
                )
                if created:
                    cls._push_incident_to_staff(incident)
                return True

            return False

        except Exception as e:
            logger.error(f"Safety Check Failure: {e}")
            return False
