from django.db.models import Q
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Ride, ChatMessage, Incident, Rating
from .serializers import RideSerializer, ChatMessageSerializer, IncidentSerializer, RatingSerializer
from rest_framework.views import APIView
from core_settings.models import LegalDocument
from django.utils import timezone

from .tasks import process_ride_matching
from payments.tasks import process_ride_earnings

class RideViewSet(viewsets.ModelViewSet):
    queryset = Ride.objects.all()
    serializer_class = RideSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        ride = serializer.save(rider=self.request.user)
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

    @action(detail=False, methods=['get'])
    def history(self, request):
        rides = Ride.objects.filter(rider=request.user).order_by('-created_at')
        return Response(self.get_serializer(rides, many=True).data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        ride = Ride.objects.filter(
            (Q(rider=request.user) | Q(driver=request.user)),
            status__in=['pending', 'accepted', 'arrived', 'in_progress']
        ).first()
        if ride:
            return Response(self.get_serializer(ride).data)
        # Return 200 with null to avoid Dio errors in frontend when no trip exists
        return Response(None, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def scheduled(self, request):
        rides = Ride.objects.filter(rider=request.user, is_scheduled=True).order_by('scheduled_for')
        return Response(self.get_serializer(rides, many=True).data)

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

            # 3. Fetch trip metrics (Passenger's route) - Only if destination is provided
            dist_km, duration_sec = 0.0, 0
            if d_lat and d_lng:
                try:
                    dist_km, duration_sec = GoogleMapsService.get_trip_metrics(
                        p_lat, p_lng, float(d_lat), float(d_lng)
                    )
                except Exception as e:
                    print(f"Error fetching trip metrics: {e}")
            
            # 4. Calculate Fares with ETA and Availability
            base_estimates = PricingService.calculate_fare_estimates(dist_km, duration_sec, lat=p_lat, lng=p_lng)
            final_estimates = {}
            
            for category_slug, fare in base_estimates.items():
                is_available = category_slug in category_availability
                eta_minutes = None
                
                if is_available:
                    # Calculate ETA for this category
                    c_pos = category_availability[category_slug]
                    # ETA from driver [lng, lat] to pickup [p_lat, p_lng]
                    try:
                        _, eta_seconds = GoogleMapsService.get_trip_metrics(c_pos[1], c_pos[0], p_lat, p_lng)
                        eta_minutes = max(1, int(eta_seconds // 60))
                    except Exception:
                        # Fallback to a very rough distance-based estimate if Maps fails for ETA
                        eta_minutes = 5 
                
                final_estimates[category_slug] = {
                    "fare": fare,
                    "is_available": is_available,
                    "eta_minutes": eta_minutes
                }

            # If no drivers nearby, we still return the list but informed about unavailability
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
                    payment_method=ride.payment_method or 'cash'
                )
                
                # Store ledger breakdown
                ride.base_fare_ledger = ledger['base_fare']
                ride.distance_fare_ledger = ledger['distance_fare']
                ride.waiting_fare_ledger = ledger['waiting_fee']
                ride.surge_multiplier_applied = ledger['surge_multiplier']
                ride.total_calculated_fare = ledger['total_fare']
                ride.driver_payout_amount = ledger['driver_payout']
                ride.fare = ledger['total_fare'] # User facing fare
                
                # Trigger earnings processing
                if ride.driver:
                    process_ride_earnings.delay(
                        ride.driver.id, # Driver is a User ID in my new model
                        ride.driver_payout_amount,
                        ride.id
                    )

                # Generate or Update RideReceipt (Screenshot 6, Automated Receipts)
                from .models import RideReceipt
                receipt_no = f"FR-{ride.id.hex[:8].upper()}-{timezone.now().strftime('%y%m%d')}"
                receipt, created = RideReceipt.objects.update_or_create(
                    ride=ride,
                    defaults={
                        "receipt_no": receipt_no,
                        "base_fare": ride.base_fare_ledger,
                        "distance_fare": ride.distance_fare_ledger,
                        "waiting_fee": ride.waiting_fare_ledger,
                        "cancellation_fee": ride.cancellation_fee_ledger,
                        "total_fare": ride.total_calculated_fare
                    }
                )
                
                # Trigger Receipt Email
                from integrations.email_service import EmailService
                EmailService.send_ride_receipt_email(ride, receipt)
            
            ride.save()
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
            # Determine Waypoint
            # If 'accepted', target is Pickup. If 'in_progress', target is Dropoff.
            target_lat = ride.pickup_lat if ride.status == 'accepted' else ride.dropoff_lat
            target_lng = ride.pickup_lng if ride.status == 'accepted' else ride.dropoff_lng
            
            dist_km, duration_sec = GoogleMapsService.get_trip_metrics(lat, lng, target_lat, target_lng)
            
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
            
            # (Optional) Here you would broadcast via WebSocket/Firebase
        
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
        ride.save()
        return Response(self.get_serializer(ride).data)

    @action(detail=True, methods=['post', 'put'])
    def accept(self, request, pk=None):
        ride = self.get_object()
        if ride.status != 'pending' and ride.status != 'requested':
            return Response({"error": "Ride already accepted or cancelled"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Profile check for driver name extraction
        if not hasattr(request.user, 'profile'):
             return Response({"error": "User has no profile"}, status=status.HTTP_400_BAD_REQUEST)
             
        ride.driver = request.user
        ride.status = 'accepted'
        ride.save()
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

    @action(detail=True, methods=['get'])
    def chat_history(self, request, pk=None):
        ride = self.get_object()
        
        # Only return chat history if the ride communication is still "ongoing"
        if ride.status in ['completed', 'cancelled']:
            return Response([])
            
        from .crypto_utils import ChatEncryption
        messages = ride.messages.all().order_by('created_at')
        
        # Decrypt messages for the session view
        for msg in messages:
            msg.content = ChatEncryption.decrypt(msg.content)
            
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

from drf_spectacular.utils import extend_schema, OpenApiTypes

class SystemSettingsView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, auth=[])
    def get(self, request):
        privacy = LegalDocument.objects.filter(title__icontains='privacy', is_active=True).order_by('-created_at').first()
        terms = LegalDocument.objects.filter(title__icontains='terms', is_active=True).order_by('-created_at').first()
        
        return Response({
            'privacy_policy': privacy.content if privacy else "Privacy policy coming soon.",
            'terms_conditions': terms.content if terms else "Terms and conditions coming soon."
        })
