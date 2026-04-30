import logging
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import F
from profiles.models import Profile
from rides.models import Ride
from flexy_backend.redis_client import redis_geo

logger = logging.getLogger(__name__)

class MatchingService:
    @staticmethod
    def find_nearby_drivers(ride_id, radius_km=3.0, exclude_locked=True):
        """
        Calculates a pool of verified, online drivers within the radius.
        Includes Redis-based concurrency locking check.
        """
        try:
            ride = Ride.objects.get(id=ride_id)
            if ride.status not in ['pending', 'requested']:
                return [], {}
            
            # 1. Category Matching (Restore Cascade/Auto-Upgrades - Point 3)
            requested_category = ride.preferred_vehicle_type or 'go'
            target_categories = [requested_category]
            
            if requested_category == 'go':
                target_categories.extend(['comfort', 'xl', 'exec'])
            elif requested_category == 'comfort':
                target_categories.extend(['xl', 'exec'])
            elif requested_category == 'xl':
                target_categories.extend(['exec'])
                
            # 2. Redis Geospatial Filter with Distance
            nearby_data = redis_geo.geo_radius_drivers_with_dist(ride.pickup_lat, ride.pickup_lng, radius_km)
            
            if not nearby_data:
                return [], {}
                
            # Map of driver_id -> distance for sorting later
            distance_map = {d_id: dist for d_id, dist in nearby_data}
            nearby_driver_ids = list(distance_map.keys())
            
            # 2.5 Redis Lock Filter (Point 5 - Redis Locking)
            if exclude_locked:
                nearby_driver_ids = [d_id for d_id in nearby_driver_ids if not redis_geo.is_driver_locked(d_id)]
            
            if not nearby_driver_ids:
                return [], {}
                
            # 3. DB Filter for Eligibility
            # Increase stale threshold to 4 hours (240 mins) to avoid filtering drivers waiting in one spot
            stale_threshold = timezone.now() - timezone.timedelta(hours=4)
            available_drivers = Profile.objects.filter(
                pk__in=nearby_driver_ids,
                user__role='driver',
                is_online=True,
                verification__is_verified=True,
                last_location_update__gte=stale_threshold,
                vehicles__type__in=target_categories,
                vehicles__is_active=True,
                vehicles__is_verified=True
            ).distinct()
            
            if not available_drivers.exists():
                logger.info(f"Matching debug: {len(nearby_driver_ids)} drivers nearby in Redis, but none eligible in DB. Radius: {radius_km}km. Categories: {target_categories}")
                # Log one sample driver's state if any nearby
                if nearby_driver_ids:
                    sample = Profile.objects.filter(pk=nearby_driver_ids[0]).first()
                    if sample:
                        is_stale = sample.last_location_update < stale_threshold if sample.last_location_update else True
                        logger.info(f"Sample driver {sample.pk} state: Online={sample.is_online}, Verified={getattr(sample.verification, 'is_verified', 'N/A')}, Stale={is_stale} (Last: {sample.last_location_update}), Categories={[v.type for v in sample.vehicles.all()]}")
            
            # 4. Sort by distance
            drivers_list = list(available_drivers)
            drivers_list.sort(key=lambda d: distance_map.get(str(d.pk), 999.0))
            
            return drivers_list, distance_map
            
        except Ride.DoesNotExist:
            logger.error(f"Ride {ride_id} does not exist for matching.")
            return []
        except Exception as e:
            logger.error(f"Error finding nearby drivers: {e}")
            return []

    @classmethod
    def dispatch_ride_request(cls, ride_id):
        """
        Orchestrates finding drivers and sending targeted WebSocket messages.
        """
        from rides.serializers import RideSerializer
        
        try:
            ride = Ride.objects.get(id=ride_id)
            if ride.status not in ['pending', 'requested']:
                return 0

            # 1. Get Sorted Pool with Distance Data
            # Adaptive Radius: Increase radius by 1.5km on each retry (max 15km)
            metadata = ride.dispatch_metadata or {}
            polled_ids = metadata.get('polled_driver_ids', [])
            radius = min(3.0 + (len(polled_ids) * 1.5), 15.0)
            
            drivers, current_distances = cls.find_nearby_drivers(ride_id, radius_km=radius)
            
            if not drivers:
                logger.info(f"Matching: No eligible drivers found within {radius}km for ride {ride_id}.")
                return 0

            # 2. Load Dispatch Metadata
            rejected_ids = metadata.get('rejected_driver_ids', [])
            distance_history = metadata.get('distance_history', {}) # driver_id -> last_dist
            
            # Point 2: Skip on Move Away (Efficiency Check)
            if polled_ids:
                last_id = polled_ids[-1]
                if last_id not in rejected_ids:
                    curr_dist = current_distances.get(last_id)
                    prev_dist = distance_history.get(last_id)
                    if curr_dist and prev_dist and curr_dist > prev_dist + 0.15: # Moved away by > 150m
                        logger.info(f"Matching: Driver {last_id} is moving away. Skipping to next.")
                        rejected_ids.append(last_id)
                        # Track missed opportunity for moving away
                        Profile.objects.filter(pk=last_id).update(missed_opportunities_count=F('missed_opportunities_count') + 1)

            # Point 4: Adaptive Batching (Aggressive for new apps)
            batch_size = 3 if len(drivers) > 5 else 2
            
            # 3. Find Next Target Driver(s)
            target_drivers = []
            poll_history = metadata.get('poll_history', {}) # driver_id -> last_poll_timestamp
            now_ts = timezone.now().timestamp()
            
            for d in drivers:
                d_id = str(d.pk)
                if d_id in rejected_ids:
                    continue
                
                last_poll = poll_history.get(d_id, 0)
                # Allow re-polling if never polled OR polled more than 45s ago
                if d_id not in polled_ids or (now_ts - last_poll > 45):
                    target_drivers.append(d)
                    if len(target_drivers) >= batch_size:
                        break
            
            if not target_drivers:
                # Point 6: Track Missed Opportunities for the driver who just timed out
                if polled_ids:
                    last_id = polled_ids[-1]
                    if last_id not in rejected_ids:
                        Profile.objects.filter(pk=last_id).update(missed_opportunities_count=F('missed_opportunities_count') + 1)
                logger.info(f"Matching: All available drivers for ride {ride_id} have already been polled and are in timeout.")
                return 0

            # 4. Dispatch Targeted WebSocket Messages
            ride_data = RideSerializer(ride).data
            channel_layer = get_channel_layer()
            
            for next_driver in target_drivers:
                d_id = str(next_driver.pk)
                target_group = f'driver_discovery_{next_driver.user.id}'
                async_to_sync(channel_layer.group_send)(
                    target_group,
                    {
                        'type': 'ride_update',
                        'event_type': 'ride_requested',
                        'data': ride_data
                    }
                )
                
                # 5. Update Metadata & Set Redis Lock (Point 5)
                polled_ids.append(d_id)
                poll_history[d_id] = now_ts
                distance_history[d_id] = current_distances.get(d_id)
                redis_geo.set_driver_lock(d_id, 20) # Lock for 20s dispatch window
            
            metadata['polled_driver_ids'] = polled_ids
            metadata['rejected_driver_ids'] = rejected_ids
            metadata['poll_history'] = poll_history
            metadata['distance_history'] = distance_history
            metadata['last_dispatch_at'] = timezone.now().isoformat()
            ride.dispatch_metadata = metadata
            ride.save()
            
            logger.info(f"Matching: Dispatched ride {ride_id} to {len(target_drivers)} driver(s).")
            return len(target_drivers)
            
        except Exception as e:
            logger.error(f"Error in targeted dispatch for ride {ride_id}: {e}")
            return 0
