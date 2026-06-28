from django.db.models import Q
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Ride, ChatMessage, Incident, Rating
from .serializers import RideSerializer, ChatMessageSerializer, IncidentSerializer, RatingSerializer, LiteRideSerializer
from rest_framework.views import APIView
from core_settings.models import LegalDocument
from django.utils import timezone

from .tasks import process_ride_matching
from payments.tasks import process_ride_earnings

class RideViewSet(viewsets.ModelViewSet):
    queryset = Ride.objects.all()
    serializer_class = RideSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['list', 'history']:
            return LiteRideSerializer
        return RideSerializer

    def _clear_overdue_scheduled_rides(self):
        """
        Clears (cancels) scheduled rides whose scheduled_for time is less than now
        and were never accepted (driver is null, status is pending/requested).
        """
        overdue_rides = Ride.objects.filter(
            is_scheduled=True,
            status__in=['pending', 'requested'],
            driver__isnull=True,
            scheduled_for__lt=timezone.now()
        )
        
        if overdue_rides.exists():
            for ride in overdue_rides:
                ride.status = 'cancelled'
                ride.save()
                # Broadcast update
                try:
                    self._broadcast_ride_update(ride, 'ride_cancelled')
                except Exception as e:
                    print(f"Error broadcasting scheduled ride timeout: {e}")

    def get_queryset(self):
        self._clear_overdue_scheduled_rides()
        return Ride.objects.select_related(
            'driver__profile', 
            'rider__profile', 
            'receipt'
        ).prefetch_related(
            'incidents', 
            'stops',
            'driver__profile__vehicles'
        )

    def _broadcast_ride_update(self, ride, event_type, data=None):
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'ride_{ride.id}',
                {
                    'type': 'ride_update',
                    'event_type': event_type,
                    'data': data or self.get_serializer(ride).data,
                    'sender_id': None # System broadcast
                }
            )
        except Exception as e:
            print(f"Error broadcasting {event_type} update: {e}")

    def perform_create(self, serializer):
        promo_code_str = self.request.data.get('promo_code_string')
        promo_code_obj = None
        if promo_code_str:
            from .models import PromoCode
            from rest_framework.exceptions import ValidationError
            try:
                promo_code_obj = PromoCode.objects.get(code=promo_code_str, active=True)
                if promo_code_obj.user and promo_code_obj.user != self.request.user:
                    raise ValidationError("Invalid promo code for this user.")
                if promo_code_obj.usage_limit > 0 and promo_code_obj.usage_count >= promo_code_obj.usage_limit:
                    raise ValidationError("Promo code usage limit reached.")
            except PromoCode.DoesNotExist:
                raise ValidationError("Invalid promo code.")

        ride = serializer.save(rider=self.request.user, promo_code=promo_code_obj)
        # Push the unfulfilled request to the Redis Geospatial Index for surge mapping
        try:
            from flexy_backend.redis_client import redis_geo
            redis_geo.geo_add_request(str(ride.id), ride.pickup_lat, ride.pickup_lng)
        except Exception:
            pass

        # Trigger matching asynchronously via RabbitMQ
        process_ride_matching.delay(str(ride.id))

    @action(detail=False, methods=['get'])
    def surge(self, request):
        """
        Dynamically calculate surge multiplier grid over a specified radius.
        """
        lat = float(request.query_params.get('lat', 0.0))
        lng = float(request.query_params.get('lng', 0.0))
        radius = float(request.query_params.get('radius', 5.0))
        
        if not lat or not lng:
            return Response({"error": "lat and lng required"}, status=status.HTTP_400_BAD_REQUEST)
            
        from .services.pricing_service import PricingService
        multiplier = PricingService.get_surge_multiplier(lat=lat, lng=lng, radius=radius)
        
        return Response({
            "lat": lat,
            "lng": lng,
            "radius": radius,
            "surge_multiplier": multiplier,
            "status": "active"
        })

    @action(detail=False, methods=['get'], url_path='surge/heatmap')
    def surge_heatmap(self, request):
        """
        Returns a list of surge points to draw on the driver map heatmap.
        """
        lat = float(request.query_params.get('lat', 0.0))
        lng = float(request.query_params.get('lng', 0.0))
        radius = float(request.query_params.get('radius', 5.0))
        
        if not lat or not lng:
            return Response({"error": "lat and lng required"}, status=status.HTTP_400_BAD_REQUEST)
            
        from .services.pricing_service import PricingService
        from django.utils import timezone
        from datetime import timedelta
        import random
        
        center_multiplier = PricingService.get_surge_multiplier(lat=lat, lng=lng, radius=radius)
        
        points = []
        if center_multiplier > 1.0:
            # Add center point
            points.append({
                "lat": lat,
                "lng": lng,
                "multiplier": center_multiplier,
                "expires_at": (timezone.now() + timedelta(minutes=5)).isoformat()
            })
            
            # Generate scattered nearby points to create a realistic heat blob
            num_points = random.randint(3, 8)
            for _ in range(num_points):
                offset_lat = random.uniform(-0.01, 0.01) * (radius / 5.0)
                offset_lng = random.uniform(-0.01, 0.01) * (radius / 5.0)
                pt_multiplier = round(random.uniform(1.2, center_multiplier), 1)
                points.append({
                    "lat": lat + offset_lat,
                    "lng": lng + offset_lng,
                    "multiplier": pt_multiplier,
                    "expires_at": (timezone.now() + timedelta(minutes=5)).isoformat()
                })
        
        return Response({"points": points, "status": "success"})

    @action(detail=False, methods=['get'])
    def history(self, request):
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        
        rides = self.get_queryset().filter(rider=request.user).order_by('-created_at')
        page = paginator.paginate_queryset(rides, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        return Response(self.get_serializer(rides, many=True).data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        five_mins_ago = timezone.now() - timezone.timedelta(minutes=5)
        
        # Base filter: participant in the ride AND (active status OR recently completed)
        qs = self.get_queryset().filter(
            (Q(rider=request.user) | Q(driver=request.user)),
            Q(status__in=['pending', 'accepted', 'arrived', 'in_progress']) |
            Q(status='completed', updated_at__gte=five_mins_ago)
        ).exclude(
            # Never show 'pending' scheduled rides as active on the home screen
            Q(is_scheduled=True, status='pending') |
            # Exclude accepted scheduled rides that are far in the future
            Q(is_scheduled=True, status='accepted', scheduled_for__gt=timezone.now() + timezone.timedelta(minutes=30))
        ).order_by('-updated_at')

        # Critical: Exclude rides that the user has already rated.
        # This prevents the summary sheet from reappearing if they've already finished the flow.
        rated_ride_ids = Rating.objects.filter(rater=request.user).values_list('ride_id', flat=True)
        ride = qs.exclude(id__in=rated_ride_ids).first()

        if ride:
            return Response(self.get_serializer(ride).data)
        # Return 200 with null to avoid Dio errors in frontend when no trip exists
        return Response(None, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def scheduled(self, request):
        # Only show rides that are in the future OR are already accepted/active.
        # If a ride is still 'pending' or 'requested' but the time has passed, it's considered overdue/expired.
        rides = self.get_queryset().filter(
            (Q(rider=request.user) | Q(driver=request.user)),
            (Q(is_scheduled=True) | Q(scheduled_for__isnull=False)),
            Q(status__in=['accepted', 'arrived', 'in_progress']) | 
            (Q(status__in=['pending', 'requested']) & Q(scheduled_for__gt=timezone.now()))
        ).order_by('scheduled_for')
        return Response(self.get_serializer(rides, many=True).data)

    @action(detail=False, methods=['get'])
    def opportunities(self, request):
        """
        Returns scheduled rides that are in 'pending' status for drivers to accept.
        """
        rides = self.get_queryset().filter(
            is_scheduled=True, 
            status__in=['pending', 'requested'],
            driver__isnull=True,
            scheduled_for__gt=timezone.now()
        ).order_by('scheduled_for')
        return Response(self.get_serializer(rides, many=True).data)

    @action(detail=True, methods=['post'], url_path='schedule/accept')
    def schedule_accept(self, request, pk=None):
        ride = self.get_object()
        if ride.status not in ['pending', 'requested']:
            return Response({"error": "Ride is not in pending status"}, status=status.HTTP_400_BAD_REQUEST)
        ride.driver = request.user
        ride.status = 'accepted'
        ride.save()
        self._broadcast_ride_update(ride, 'status_updated')
        return Response(self.get_serializer(ride).data)

    @action(detail=True, methods=['post'], url_path='schedule/start')
    def schedule_start(self, request, pk=None):
        ride = self.get_object()
        ride.status = 'accepted'
        ride.save()
        
        # Sync Vehicle Status to 'riding'
        from profiles.services.tracking_service import TrackingService
        TrackingService.set_driver_ride_status(str(request.user.id), is_riding=True)
        
        self._broadcast_ride_update(ride, 'status_updated')
        return Response(self.get_serializer(ride).data)

    @action(detail=False, methods=['post'])
    def schedule(self, request):
        """
        Creates a future-dated ride request without immediate matching.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            scheduled_for = serializer.validated_data.get('scheduled_for')
            if not scheduled_for:
                return Response({"error": "scheduled_for is required for scheduled rides"}, status=status.HTTP_400_BAD_REQUEST)
            
            if scheduled_for <= timezone.now():
                return Response({"error": "scheduled_for must be in the future"}, status=status.HTTP_400_BAD_REQUEST)

            ride = serializer.save(
                rider=self.request.user,
                is_scheduled=True,
                status='pending'
            )
            
            # Explicitly set is_scheduled to True to ensure it wins over any data in the serializer
            needs_update = False
            update_fields = []
            if not ride.is_scheduled:
                ride.is_scheduled = True
                needs_update = True
                update_fields.append('is_scheduled')
            if ride.status != 'pending':
                ride.status = 'pending'
                needs_update = True
                update_fields.append('status')
                
            if needs_update:
                ride.save(update_fields=update_fields)
                
            return Response(self.get_serializer(ride).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=['get', 'post'])
    def favorites(self, request):
        if request.method == 'GET':
            from .models import FavoriteLocation
            from .serializers import FavoriteLocationSerializer
            favs = FavoriteLocation.objects.filter(user=request.user)
            return Response(FavoriteLocationSerializer(favs, many=True).data)
        else:
            from .serializers import FavoriteLocationSerializer
            serializer = FavoriteLocationSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def estimate(self, request):
        """
        Calculates dynamic fares and real-time ETA for all categories.
        Only shows categories with available drivers within 5km.
        """
        try:
            p_lat = float(request.query_params.get('pickup_lat'))
            p_lng = float(request.query_params.get('pickup_lng'))
            d_lat = request.query_params.get('dropoff_lat')
            d_lng = request.query_params.get('dropoff_lng')
            
            from .services.pricing_service import PricingService
            from flexy_backend.redis_client import redis_geo
            from vehicles.models import Vehicle
            from integrations.google_maps import GoogleMapsService
            
            # 1. Broad fetch for nearby drivers (5.0 km radius)
            nearby_ids = redis_geo.geo_radius_drivers(p_lat, p_lng, 5.0)
            
            # 2. Map drivers to their vehicle categories
            active_vehicles = Vehicle.objects.filter(
                driver_id__in=nearby_ids,  # Redis stores profile.pk, driver FK points to Profile
                is_active=True,
                is_verified=True
            ).select_related('driver')
            
            # Group driver positions by category
            driver_positions = redis_geo.get_driver_positions(nearby_ids)
            category_availability = {} # category_slug -> closest_driver_coords
            
            for v in active_vehicles:
                driver_id = str(v.driver_id)
                if driver_id in driver_positions:
                    pos = driver_positions[driver_id] # [lng, lat]
                    if v.type not in category_availability:
                        category_availability[v.type] = pos

            # 3. Fetch trip metrics (Passenger's route)
            import json
            stops_raw = request.query_params.get('stops') or request.data.get('stops', [])
            if isinstance(stops_raw, str):
                try:
                    stops = json.loads(stops_raw)
                except:
                    stops = []
            else:
                stops = stops_raw

            dist_km, duration_sec, traffic_sec = 0.0, 0, 0
            if d_lat and d_lng:
                try:
                    # Pass waypoints to Directions API for accurate multi-stop distance
                    dist_km, duration_sec, traffic_sec = GoogleMapsService.get_trip_metrics(
                        p_lat, p_lng, float(d_lat), float(d_lng),
                        waypoints=stops
                    )
                except Exception as e:
                    print(f"Error fetching trip metrics: {e}")
                
                print(f"DEBUG ESTIMATE: dist_km={dist_km}, duration_sec={duration_sec}, traffic_sec={traffic_sec}, stops={len(stops)}")
            
            # 4. Calculate Fares with ETA and Availability
            base_estimates = PricingService.calculate_fare_estimates(
                dist_km, duration_sec, 
                lat=p_lat, lng=p_lng,
                num_stops=len(stops),
                duration_in_traffic_sec=traffic_sec
            )
            final_estimates = {}
            
            for category_slug, fare in base_estimates.items():
                is_real_time_available = category_slug in category_availability
                eta_minutes = None
                
                if is_real_time_available:
                    # Calculate ETA for this category
                    c_pos = category_availability[category_slug]
                    # ETA from driver [lng, lat] to pickup [p_lat, p_lng]
                    try:
                        from .services.geo_service import GeoService
                        driver_lat = float(c_pos[1])
                        driver_lng = float(c_pos[0])
                        distance_km = GeoService.calculate_haversine_distance(driver_lat, driver_lng, float(p_lat), float(p_lng))
                        # Assume avg city speed of 30 km/h (0.5 km/min)
                        eta_minutes = max(1, int(distance_km / 0.5))
                    except Exception:
                        # Fallback to a very rough distance-based estimate if calculation fails
                        eta_minutes = 5
                
                final_estimates[category_slug] = {
                    "fare": fare,
                    "is_available": True, # Always selectable (Restore Point 4)
                    "real_time_available": is_real_time_available,
                    "eta_minutes": eta_minutes
                }

            # If no drivers nearby, we still return the list but informed about unavailability
            if not final_estimates:
                return Response({"error": "No vehicle categories available at this time."}, status=status.HTTP_404_NOT_FOUND)

            # Standard data for the summary view
            standard_data = final_estimates.get('standard') or final_estimates.get('go') or list(final_estimates.values())[0]
            
            return Response({
                "estimated_fare": standard_data['fare'],
                "is_available": standard_data['is_available'],
                "eta_minutes": standard_data['eta_minutes'],
                "estimates": final_estimates,
                "distance_km": round(dist_km, 2),
                "duration_seconds": int(duration_sec),
                "duration_text": f"{int(duration_sec // 60)} mins",
                "distance_text": f"{round(dist_km, 1)} km",
                "currency": "GHS"
            })


        except (TypeError, ValueError) as e:
            return Response({"error": "Missing or invalid coordinates"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post', 'put', 'patch'])
    def status(self, request, pk=None):
        ride = self.get_object()
        old_status = ride.status
        new_status = request.data.get('status')
        
        if new_status in [choice[0] for choice in Ride.STATUS_CHOICES]:
            ride.status = new_status
            
            # If completed, calculate final 8-stage pricing ledger (Screenshot 7)
            # Only execute this logic if the ride is transitioning to 'completed' status
            if new_status == 'completed' and old_status != 'completed':
                from .services.pricing_service import PricingService
                actual_distance = request.data.get('distance', ride.distance)
                waiting_mins = request.data.get('waiting_minutes', 0)
                
                ledger = PricingService.compute_final_fare(
                    distance_km=actual_distance,
                    vehicle_category_slug=ride.preferred_vehicle_type or 'standard',
                    lat=ride.pickup_lat,
                    lng=ride.pickup_lng,
                    waiting_minutes=waiting_mins,
                    payment_method=ride.payment_method or 'cash',
                    num_stops=ride.stops.count()
                )
                
                # Apply PromoCode Discount if applicable
                discount_to_apply = 0.0
                if ride.promo_code:
                    discount_to_apply = min(ride.promo_code.value, ledger['total_fare'])
                    ride.promo_code.usage_count += 1
                    ride.promo_code.save()
                    
                ride.discount_amount = discount_to_apply
                
                # Store ledger breakdown
                ride.base_fare_ledger = ledger['base_fare']
                ride.distance_fare_ledger = ledger['distance_fare']
                ride.stops_fee_ledger = ledger['stops_fee']
                ride.waiting_fare_ledger = ledger['waiting_fee']
                ride.surge_multiplier_applied = ledger['surge_multiplier']
                ride.total_calculated_fare = ledger['total_fare'] - discount_to_apply
                ride.driver_payout_amount = ledger['driver_payout']
                ride.fare = ledger['total_fare'] - discount_to_apply # User facing fare
                
                # Trigger earnings processing
                from payments.tasks import process_ride_earnings
                process_ride_earnings.delay(
                    str(ride.driver.id), 
                    float(ride.fare), 
                    str(ride.id),
                    metadata={
                        "pickup_address": ride.pickup_address,
                        "dropoff_address": ride.dropoff_address,
                        "ride_id": str(ride.id)
                    }
                )

                # --- REFERRAL REWARD LOGIC ---
                if hasattr(ride.rider, 'profile'):
                    profile = ride.rider.profile
                    # Check if this is the rider's first completed ride
                    is_first_ride = Ride.objects.filter(rider=ride.rider, status='completed').count() == 0
                    if is_first_ride and profile.referred_by:
                        import string
                        import random
                        from .models import PromoCode
                        from notification.utils import send_notification
                        
                        # Generate code for Rider
                        rider_code_str = f"REF-{profile.referred_by.referral_code}-{random.randint(100,999)}"
                        PromoCode.objects.create(
                            user=ride.rider,
                            code=rider_code_str,
                            type='fixed',
                            value=5.0,
                            usage_limit=1
                        )
                        send_notification(
                            ride.rider,
                            title="Referral Bonus! 🎉",
                            body=f"Enjoy GH₵ 5.00 off your next ride with promo code {rider_code_str}.",
                            type='PUSH'
                        )
                        
                        # Generate code for Referrer
                        referrer_code_str = f"REF-{profile.referral_code}-{random.randint(100,999)}"
                        referrer = profile.referred_by
                        PromoCode.objects.create(
                            user=referrer.user,
                            code=referrer_code_str,
                            type='fixed',
                            value=5.0,
                            usage_limit=1
                        )
                        send_notification(
                            referrer.user,
                            title="Referral Reward! 🎁",
                            body=f"Your friend took their first ride! Here is GH₵ 5.00 off: {referrer_code_str}.",
                            type='PUSH'
                        )
                        
                        # Update stats
                        referrer.total_referrals += 1
                        referrer.total_referral_earnings += 5.0
                        referrer.save()
                # -----------------------------

                # Generate or Update RideReceipt (Screenshot 6, Automated Receipts)
                from .models import RideReceipt
                receipt_no = f"FR-{ride.id.hex[:8].upper()}-{timezone.now().strftime('%y%m%d')}"
                receipt, created = RideReceipt.objects.update_or_create(
                    ride=ride,
                    defaults={
                        "receipt_no": receipt_no,
                        "base_fare": ride.base_fare_ledger,
                        "distance_fare": ride.distance_fare_ledger,
                        "stops_fee": ride.stops_fee_ledger,
                        "waiting_fee": ride.waiting_fare_ledger,
                        "cancellation_fee": ride.cancellation_fee_ledger,
                        "total_fare": ride.total_calculated_fare
                    }
                )
                
                # Trigger Receipt Email
                from integrations.email_service import EmailService
                EmailService.send_ride_receipt_email(ride, receipt)
            
            # If transitioning FROM active states TO terminal states, reset vehicle status
            if new_status in ['completed', 'cancelled'] and old_status in ['accepted', 'arrived', 'in_progress']:
                if ride.driver:
                    from profiles.services.tracking_service import TrackingService
                    TrackingService.set_driver_ride_status(str(ride.driver.id), is_riding=False)
            
            ride.save()
            
            # Broadcast the status update via WebSocket room (Screenshot 6)
            self._broadcast_ride_update(ride, 'status_updated')

            # Send Push Notification to Passenger
            try:
                from notification.utils import send_notification
                if new_status != old_status:
                    title = "Ride Update"
                    body = None
                    if new_status == 'accepted':
                        body = f"Great news! {ride.driver.profile.full_name} has accepted your ride request."
                    elif new_status == 'arrived':
                        body = f"Your driver has arrived at {ride.pickup_address}."
                    elif new_status == 'in_progress':
                        body = "Your trip has started. Enjoy the ride!"
                    elif new_status == 'completed':
                        body = f"You've arrived! Your total is GH₵ {ride.fare:.2f}."
                    
                    if body:
                        # Default settings
                        channel_id = None
                        sound = None
                        
                        # Use horn sound for arrival
                        if new_status == 'arrived':
                            channel_id = 'high_priority_rides'
                            sound = 'horn'
                            
                        save_in_db = (new_status == 'completed')
                        send_notification(
                            ride.rider, 
                            title=title, 
                            body=body, 
                            type='PUSH', 
                            ref_id=ride.id,
                            android_channel_id=channel_id,
                            android_sound=sound,
                            ios_sound=f'{sound}.wav' if sound else None,
                            save_in_db=save_in_db
                        )
            except Exception as e:
                print(f"Notification error: {e}")

            return Response(self.get_serializer(ride).data)
        return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def track(self, request, pk=None):
        """
        Receives driver coordinates and updates remaining distance/ETA.
        Includes throttling to optimize Google Maps API usage.
        """
        ride = self.get_object()
        lat = float(request.data.get('lat'))
        lng = float(request.data.get('lng'))
        
        from django.utils import timezone
        from .services.pricing_service import PricingService
        from .services.geo_service import GeoService
        from integrations.google_maps import GoogleMapsService
        import math

        now = timezone.now()
        should_update_eta = False
        
        # 1. Throttling Logic (Screenshot 6, Point 8)
        if not ride.last_tracking_time:
            should_update_eta = True
        else:
            time_diff = (now - ride.last_tracking_time).total_seconds()
            # If 60 seconds passed since last Google call
            if time_diff >= 60:
                should_update_eta = True
            
            # OR if moved more than 200 meters
            if not should_update_eta and ride.last_lat_update and ride.last_lng_update:
                dist_moved = GeoService.calculate_haversine_distance(
                    lat, lng, 
                    ride.last_lat_update, ride.last_lng_update
                )
                if dist_moved >= 200:
                    should_update_eta = True

        if should_update_eta:
            # Determine Target Milestone
            target_lat, target_lng = ride.dropoff_lat, ride.dropoff_lng
            
            if ride.status in ['accepted', 'arrived', 'pending_pickup']:
                target_lat, target_lng = ride.pickup_lat, ride.pickup_lng
            elif ride.status == 'in_progress':
                # Check for the next pending intermediate stop
                next_stop = ride.stops.filter(status__in=['pending', 'arrived']).order_by('stop_order').first()
                if next_stop:
                    target_lat, target_lng = next_stop.latitude, next_stop.longitude

            dist_km, duration_sec, _ = GoogleMapsService.get_trip_metrics(lat, lng, target_lat, target_lng)
            
            ride.distance_remaining = dist_km
            ride.duration_remaining = duration_sec
            ride.estimated_eta = duration_sec / 60.0
            ride.last_lat_update = lat
            ride.last_lng_update = lng
            ride.last_tracking_time = now
            ride.save()
            
            # Keep Redis matched tracking up to date
            if ride.driver and hasattr(ride.driver, 'profile'):
                from flexy_backend.redis_client import redis_geo
                redis_geo.geo_add_driver(str(ride.driver.profile.id), lat, lng)
            
            # Broadcast the metrics update via WebSocket room (Screenshot 6)
            self._broadcast_ride_update(ride, 'metrics_updated', data={
                'distance_remaining': ride.distance_remaining,
                'duration_remaining': ride.duration_remaining,
                'estimated_eta': ride.estimated_eta,
            })
        
        return Response({
            "status": ride.status,
            "distance_remaining": ride.distance_remaining,
            "duration_remaining": ride.duration_remaining,
            "updated_at": ride.last_tracking_time
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        ride = self.get_object()
        if ride.status in ['completed', 'cancelled']:
            return Response(
                {"error": f"Ride is already {ride.status} and cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if request.user != ride.rider and request.user != ride.driver:
            return Response(
                {"error": "You are not authorized to cancel this ride."},
                status=status.HTTP_403_FORBIDDEN
            )
        ride.status = 'cancelled'
        if ride.driver:
            from profiles.services.tracking_service import TrackingService
            TrackingService.set_driver_ride_status(str(ride.driver.id), is_riding=False)
        ride.save()
        
        self._broadcast_ride_update(ride, 'status_updated')
        
        # Notify discovery stream to remove request from polled drivers
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            metadata = ride.dispatch_metadata or {}
            polled_ids = metadata.get('polled_driver_ids', [])
            for p_id in polled_ids:
                from profiles.models import Profile
                profile = Profile.objects.filter(pk=p_id).first()
                if profile:
                    target_group = f'driver_discovery_{profile.user.id}'
                    async_to_sync(channel_layer.group_send)(
                        target_group,
                        {
                            'type': 'ride_update',
                            'event_type': 'ride_cancelled',
                            'data': {'ride_id': str(ride.id)}
                        }
                    )
        except Exception:
            pass
        
        return Response(self.get_serializer(ride).data)

    @action(detail=True, methods=['post', 'put'])
    def accept(self, request, pk=None):
        from django.db import transaction
        from .models import Ride
        
        with transaction.atomic():
            try:
                ride = Ride.objects.select_for_update().get(pk=pk)
            except Ride.DoesNotExist:
                return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

            self.check_object_permissions(request, ride)
            print(f"DEBUG: Driver {request.user.id} attempting to accept ride {ride.id}. Current status: {ride.status}")
            
            if ride.status != 'pending' and ride.status != 'requested':
                print(f"DEBUG: Acceptance failed for ride {ride.id}. Status is {ride.status}")
                return Response({"error": "Ride already accepted or cancelled"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Profile check for driver name extraction
            if not hasattr(request.user, 'profile'):
                 print(f"DEBUG: Acceptance failed for ride {ride.id}. Driver {request.user.id} has no profile.")
                 return Response({"error": "User has no profile"}, status=status.HTTP_400_BAD_REQUEST)
                 
            ride.driver = request.user
            ride.status = 'accepted'
            ride.save()
        
        # Sync Vehicle Status to 'riding'
        from profiles.services.tracking_service import TrackingService
        TrackingService.set_driver_ride_status(str(request.user.id), is_riding=True)
        
        print(f"DEBUG: Ride {ride.id} successfully accepted by driver {request.user.id}")
        self._broadcast_ride_update(ride, 'status_updated')
        
        return Response(self.get_serializer(ride).data)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        ride = self.get_object()
        if ride.status not in ['pending', 'requested']:
             return Response({"error": "Ride is no longer available"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark driver as rejected for this ride
        metadata = ride.dispatch_metadata or {}
        rejected_ids = metadata.get('rejected_driver_ids', [])
        d_id = str(request.user.id)
        if d_id not in rejected_ids:
            rejected_ids.append(d_id)
            metadata['rejected_driver_ids'] = rejected_ids
            ride.dispatch_metadata = metadata
            ride.save()
            
        # Trigger immediate re-dispatch for the next nearest driver
        from .tasks import process_ride_matching
        process_ride_matching.delay(str(ride.id))
        
        return Response({"status": "declined"})

    @action(detail=True, methods=['post'])
    def sos(self, request, pk=None):
        ride = self.get_object()
        incident = Incident.objects.create(
            ride=ride,
            reporter=request.user,
            type='SOS',
            description=request.data.get('description', 'SOS Triggered'),
            location_lat=request.data.get('lat'),
            location_lng=request.data.get('lng')
        )
        
        # Trigger Admin Email Notification
        from integrations.email_service import EmailService
        EmailService.send_sos_alert_email(incident)

        # Broadcast to admin_alerts group via Django Channels
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                'admin_alerts',
                {
                    'type': 'admin_alert',
                    'data': {
                        'incident_id': str(incident.id),
                        'ride_id': str(ride.id),
                        'reporter_email': incident.reporter.email if incident.reporter else 'Anonymous',
                        'type': incident.type,
                        'description': incident.description,
                        'location_lat': incident.location_lat,
                        'location_lng': incident.location_lng,
                        'created_at': incident.created_at.isoformat()
                    }
                }
            )
        
        return Response(IncidentSerializer(incident).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        ride = self.get_object()
        
        # Identify rater and ratee
        rater = request.user
        if rater == ride.rider:
            ratee = ride.driver
            rater_type = 'rider'
        elif rater == ride.driver:
            ratee = ride.rider
            rater_type = 'driver'
        else:
            return Response({"error": "You are not a participant in this ride"}, status=status.HTTP_403_FORBIDDEN)
            
        if not ratee:
            return Response({"error": "No counterparty to rate"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if already rated by this user
        existing = Rating.objects.filter(ride=ride, rater=rater).first()
        if existing:
            return Response({"error": "You have already rated this ride"}, status=status.HTTP_400_BAD_REQUEST)

        # Prepare data for serializer
        data = request.data.copy()
        data['ride'] = ride.id
        data['rater'] = rater.id
        data['ratee'] = ratee.id
        data['rater_type'] = rater_type
        
        serializer = RatingSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='stops/(?P<stop_id>[^/.]+)/status')
    def update_stop_status(self, request, pk=None, stop_id=None):
        """
        Allows drivers to mark individual intermediate stops as 'arrived' or 'completed'.
        """
        ride = self.get_object()
        from .models import RideStop
        try:
            stop = RideStop.objects.get(id=stop_id, ride=ride)
            new_status = request.data.get('status')
            
            if new_status in ['pending', 'arrived', 'completed']:
                stop.status = new_status
                if new_status == 'arrived':
                    stop.arrived_at = timezone.now()
                elif new_status == 'completed':
                    stop.completed_at = timezone.now()
                stop.save()
                
                # Broadcast the update via WebSocket so the passenger's map updates
                self._broadcast_ride_update(ride, 'stops_updated')
                
                # Send Push Notification to Passenger
                try:
                    from notification.utils import send_notification
                    title = "Stop Update"
                    if new_status == 'arrived':
                        body = f"Your driver has arrived at {stop.address}."
                    elif new_status == 'completed':
                        body = f"Driver completed the stop at {stop.address} and is moving to the next destination."
                    else:
                        body = f"Stop at {stop.address} is now {new_status}."
                    
                    send_notification(
                        ride.rider,
                        title=title,
                        body=body,
                        type='PUSH',
                        ref_id=ride.id,
                        extra_data={'notification_type': 'RIDE_ACTIVE'},
                        save_in_db=False
                    )
                except Exception as e:
                    print(f"Notification error: {e}")
                
                return Response(self.get_serializer(ride).data)
            return Response({"error": "Invalid status. Must be pending, arrived, or completed."}, status=status.HTTP_400_BAD_REQUEST)
        except RideStop.DoesNotExist:
            return Response({"error": "Stop not found for this ride."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def chat_history(self, request, pk=None):
        from .crypto_utils import ChatEncryption
        from courier.models import Delivery
        from django.utils import timezone
        
        messages = []
        try:
            ride = Ride.objects.get(pk=pk)
            # Only return chat history if the ride communication is still "ongoing" 
            # or within a 30-minute grace period for post-ride coordination (lost items, etc)
            if ride.status in ['completed', 'cancelled']:
                time_since_terminal = (timezone.now() - ride.updated_at).total_seconds()
                if time_since_terminal > 1800: # 30 minutes
                    return Response([])
            messages = ride.messages.select_related('sender').all().order_by('created_at')
        except Ride.DoesNotExist:
            try:
                delivery = Delivery.objects.get(pk=pk)
                if delivery.status in ['DELIVERED', 'CANCELLED']:
                    time_since_terminal = (timezone.now() - delivery.updated_at).total_seconds()
                    if time_since_terminal > 1800: # 30 minutes
                        return Response([])
                messages = delivery.messages.select_related('sender').all().order_by('created_at')
            except Delivery.DoesNotExist:
                return Response({"detail": "Not found."}, status=404)
            
        # Decrypt messages for the session view
        for msg in messages:
            msg.content = ChatEncryption.decrypt(msg.content)
            
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        ride = self.get_object()
        share_url = f"https://flexyridegh.com/track/{ride.id}"
        return Response({"share_url": share_url})

    @action(detail=True, methods=['put', 'patch', 'post'])
    def destination(self, request, pk=None):
        """
        Updates the ride dropoff destination and/or its intermediate stops.
        Recalculates trip metrics (fare, distance) dynamically.
        """
        ride = self.get_object()
        
        # 1. Update final destination if provided
        dropoff_lat = request.data.get('dropoff_lat')
        dropoff_lng = request.data.get('dropoff_lng')
        dropoff_address = request.data.get('dropoff_address')
        
        if dropoff_lat is not None:
            ride.dropoff_lat = float(dropoff_lat)
        if dropoff_lng is not None:
            ride.dropoff_lng = float(dropoff_lng)
        if dropoff_address is not None:
            ride.dropoff_address = dropoff_address
            
        # 2. Update intermediate stops if provided
        stops_data = request.data.get('stops')
        if stops_data is not None:
            from .models import RideStop
            # Parse stops_data if it comes as a string (json encoded)
            import json
            if isinstance(stops_data, str):
                try:
                    stops_data = json.loads(stops_data)
                except Exception:
                    pass
            
            if isinstance(stops_data, list):
                # Synchronize stops
                existing_stops = {str(s.id): s for s in ride.stops.all()}
                new_stop_ids = []
                
                for idx, stop_item in enumerate(stops_data):
                    stop_id = stop_item.get('id')
                    address = stop_item.get('address')
                    lat = float(stop_item.get('latitude'))
                    lng = float(stop_item.get('longitude'))
                    order = stop_item.get('stop_order', idx + 1)
                    
                    if stop_id and stop_id in existing_stops:
                        stop_obj = existing_stops[stop_id]
                        stop_obj.address = address
                        stop_obj.latitude = lat
                        stop_obj.longitude = lng
                        stop_obj.stop_order = order
                        stop_obj.save()
                        new_stop_ids.append(stop_id)
                    else:
                        new_stop = RideStop.objects.create(
                            ride=ride,
                            address=address,
                            latitude=lat,
                            longitude=lng,
                            stop_order=order,
                            status='pending'
                        )
                        new_stop_ids.append(str(new_stop.id))
                        
                # Delete any existing stops that were omitted (only if pending)
                for s_id, stop_obj in existing_stops.items():
                    if s_id not in new_stop_ids and stop_obj.status == 'pending':
                        stop_obj.delete()

        # 3. Recalculate distance and estimated fare based on the new route
        from integrations.google_maps import GoogleMapsService
        from .services.pricing_service import PricingService
        
        origin_lat = ride.pickup_lat
        origin_lng = ride.pickup_lng
        if ride.status == 'in_progress' and ride.last_lat_update and ride.last_lng_update:
            origin_lat = ride.last_lat_update
            origin_lng = ride.last_lng_update
            
        waypoints = []
        for stop in ride.stops.filter(status='pending').order_by('stop_order'):
            waypoints.append((stop.latitude, stop.longitude))
            
        try:
            metrics = GoogleMapsService.get_trip_metrics(
                origin_lat, origin_lng,
                ride.dropoff_lat, ride.dropoff_lng,
                waypoints=waypoints
            )
            dist_km = metrics['distance_km']
            duration_sec = metrics['duration_seconds']
            
            estimates = PricingService.calculate_fare_estimates(
                dist_km, duration_sec,
                lat=origin_lat, lng=origin_lng,
                num_stops=len(waypoints)
            )
            pref_cat = ride.preferred_vehicle_type or 'standard'
            new_fare = estimates.get(pref_cat) or list(estimates.values())[0]
            
            ride.distance = dist_km
            ride.fare = new_fare
        except Exception as e:
            print(f"Error recalculating route on destination edit: {e}")
            
        ride.save()
        
        # 4. Broadcast the update
        self._broadcast_ride_update(ride, 'destination_updated')
        
        # Send push notification to driver
        if ride.driver:
            try:
                from notification.utils import send_notification
                send_notification(
                    user=ride.driver,
                    title="📍 Route Updated",
                    body=f"The passenger has updated the destination or stop locations.",
                    type='PUSH',
                    ref_id=str(ride.id),
                    extra_data={'notification_type': 'RIDE_ACTIVE'},
                    save_in_db=False
                )
            except Exception as e:
                print(f"Error sending route update push to driver: {e}")
                
        return Response(self.get_serializer(ride).data)


from drf_spectacular.utils import extend_schema, OpenApiTypes

class SystemSettingsView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, auth=[])
    def get(self, request):
        from core_settings.models import SiteSetting
        from website.models import LegalDocument
        from django.core.cache import cache
        
        cached_settings = cache.get('system_settings')
        if cached_settings:
            return Response(cached_settings)

        privacy = LegalDocument.objects.filter(document_type='privacy').order_by('-last_updated').first()
        terms = LegalDocument.objects.filter(document_type='terms').order_by('-last_updated').first()
        about = LegalDocument.objects.filter(document_type='about').order_by('-last_updated').first()
        
        support_email = SiteSetting.objects.filter(key='support_email').first()
        support_phone = SiteSetting.objects.filter(key='support_phone').first()
        
        settings_data = {
            "privacy_policy": privacy.content if privacy else "",
            "terms_of_service": terms.content if terms else "",
            "about_us": about.content if about else "",
            "support_email": support_email.value if support_email else "support@flexyridegh.com",
            "support_phone": support_phone.value if support_phone else "+233 20 000 0000"
        }
        
        cache.set('system_settings', settings_data, timeout=86400) # Cache for 24 hours
        return Response(settings_data)
