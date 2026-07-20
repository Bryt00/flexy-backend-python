from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Delivery
from .serializers import DeliverySerializer
from rides.utils import FareCalculator, GeospatialUtils
from integrations.google_maps import GoogleMapsService
from .utils import CourierFareCalculator

class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]

    def _check_and_expire_deliveries(self):
        """
        Auto-expires pending deliveries that have been searching for more than 3 minutes.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        timeout_threshold = timezone.now() - timedelta(minutes=3)
        expired_deliveries = Delivery.objects.filter(
            status='PENDING',
            created_at__lt=timeout_threshold
        )
        
        if expired_deliveries.exists():
            channel_layer = get_channel_layer()
            for delivery in expired_deliveries:
                delivery.status = 'CANCELLED'
                delivery.save()
                
                # Broadcast status update
                try:
                    async_to_sync(channel_layer.group_send)(
                        f'delivery_{delivery.id}',
                        {
                            'type': 'delivery_broadcast',
                            'message_type': 'status_update',
                            'data': DeliverySerializer(delivery).data
                        }
                    )
                except Exception as e:
                    print(f"Error broadcasting delivery timeout: {e}")
                    
                # Broadcast removal to discovery stream
                try:
                    async_to_sync(channel_layer.group_send)(
                        'delivery_discovery',
                        {
                            'type': 'delivery_broadcast',
                            'message_type': 'delivery_taken',
                            'data': {'delivery_id': str(delivery.id)}
                        }
                    )
                except Exception as e:
                    print(f"Error broadcasting delivery discovery removal: {e}")

    def _broadcast_delivery_update(self, delivery, message_type, data=None):
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'delivery_{delivery.id}',
                {
                    'type': 'delivery_broadcast',
                    'message_type': message_type,
                    'data': data or DeliverySerializer(delivery).data
                }
            )
        except Exception as e:
            print(f"Error broadcasting delivery {message_type}: {e}")

    def _broadcast_discovery(self, message_type, data):
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'delivery_discovery',
                {
                    'type': 'delivery_broadcast',
                    'message_type': message_type,
                    'data': data
                }
            )
        except Exception as e:
            print(f"Error broadcasting discovery {message_type}: {e}")

    def get_queryset(self):
        self._check_and_expire_deliveries()
        # Passengers see their requested deliveries, drivers see assigned ones OR PENDING ones
        user = self.request.user
        qs = Delivery.objects.select_related('passenger', 'driver').prefetch_related('proofs')
        if user.role == 'driver':
            from django.db.models import Q
            return qs.filter(Q(driver=user.profile) | Q(status='PENDING'))
        return qs.filter(passenger=user)

    def perform_create(self, serializer):
        # 1. Calculate fare using coordinates
        pickup_lat = serializer.validated_data.get('pickup_lat')
        pickup_lng = serializer.validated_data.get('pickup_lng')
        dropoff_lat = serializer.validated_data.get('dropoff_lat')
        dropoff_lng = serializer.validated_data.get('dropoff_lng')
        
        distance_km = 0.0
        duration_sec = 0.0
        total_fare = 0.0
        base_fare = 0.0
        distance_fee = 0.0
        
        try:
            distance_km, duration_sec, _ = GoogleMapsService.get_trip_metrics(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
            
            vehicle_type_id = serializer.validated_data.get('vehicle_type')
            category_id = serializer.validated_data.get('item_category')
            weight_tier_id = serializer.validated_data.get('weight_tier')

            ledger = CourierFareCalculator.compute_final_fare(
                distance_km=distance_km, 
                vehicle_type_id=vehicle_type_id.id if vehicle_type_id else None,
                category_id=category_id.id if category_id else None,
                weight_tier_id=weight_tier_id.id if weight_tier_id else None,
                lat=pickup_lat,
                lng=pickup_lng
            )
            total_fare = ledger.get('total_fare', 0.0)
            base_fare = ledger.get('base_fare', 0.0)
            distance_fee = ledger.get('distance_fare', 0.0)
        except Exception as e:
            print(f"Error calculating delivery metrics/fares: {e}")
            
        delivery = serializer.save(
            passenger=self.request.user,
            distance=distance_km,
            estimated_eta=duration_sec / 60.0,
            estimated_fare=total_fare,
            base_fare=base_fare,
            distance_fee=distance_fee,
            final_fare=total_fare
        )
        
        # Broadcast to available drivers (Discovery stream)
        self._broadcast_discovery('new_delivery', DeliverySerializer(delivery).data)

        # Notify active delivery drivers via push notifications within 15km
        try:
            from profiles.models import Profile
            from notification.utils import send_notification
            from django.db.models import Q
            from core_settings.models import VehicleCategory
            from django.contrib.gis.geos import Point
            
            restricted_slugs = list(VehicleCategory.objects.filter(is_passenger_allowed=False).values_list('slug', flat=True))
            
            eligible_drivers = Profile.objects.filter(
                Q(receive_deliveries=True) |
                Q(vehicles__type__in=restricted_slugs, vehicles__is_active=True)
            ).filter(is_online=True).select_related('user').distinct()
            
            for driver in eligible_drivers:
                if driver.last_lat and driver.last_lng and pickup_lat and pickup_lng:
                    dist = GeospatialUtils.calculate_haversine_distance(
                        driver.last_lat, driver.last_lng, 
                        pickup_lat, pickup_lng
                    ) / 1000.0
                    if dist > 15.0: # 15km radius
                        continue
                
                # Geofence check for deliveries
                geofence_passed = True
                active_vehicle = driver.vehicles.filter(is_active=True).first()
                if active_vehicle:
                    try:
                        category = VehicleCategory.objects.get(slug=active_vehicle.type)
                        if category.is_delivery_geofenced:
                            pickup_point = Point(float(pickup_lng), float(pickup_lat), srid=4326) if pickup_lat and pickup_lng else None
                            dropoff_point = Point(float(dropoff_lng), float(dropoff_lat), srid=4326) if dropoff_lat and dropoff_lng else None
                            if not pickup_point or not dropoff_point:
                                geofence_passed = False
                            else:
                                allowed_areas = category.allowed_service_areas.all()
                                if allowed_areas.exists():
                                    pickup_in = any(area.polygon.contains(pickup_point) for area in allowed_areas)
                                    dropoff_in = any(area.polygon.contains(dropoff_point) for area in allowed_areas)
                                    if not (pickup_in and dropoff_in):
                                        geofence_passed = False
                                else:
                                    geofence_passed = False
                    except VehicleCategory.DoesNotExist:
                        pass
                
                if not geofence_passed:
                    continue
                
                send_notification(
                    user=driver.user,
                    title="📦 New Delivery Opportunity!",
                    body=f"Pickup: {delivery.pickup_address}\nDropoff: {delivery.dropoff_address}",
                    type='PUSH',
                    ref_id=str(delivery.id),
                    extra_data={'notification_type': 'DELIVERY_OPPORTUNITY'},
                    save_in_db=False
                )
        except Exception as e:
            print(f"Error sending delivery notifications to drivers: {e}")

    @action(detail=False, methods=['get'])
    def estimate(self, request):
        """
        Calculates delivery fare estimates based on distance and vehicle category.
        """
        try:
            p_lat = float(request.query_params.get('pickup_lat'))
            p_lng = float(request.query_params.get('pickup_lng'))
            d_lat = float(request.query_params.get('dropoff_lat'))
            d_lng = float(request.query_params.get('dropoff_lng'))
            
            vehicle_type_id = request.query_params.get('vehicle_type_id') or request.query_params.get('vehicle_type')
            category_id = request.query_params.get('category_id') or request.query_params.get('item_category')
            weight_tier_id = request.query_params.get('weight_tier_id') or request.query_params.get('weight_tier')
            
            # 1. Fetch real metrics from Google
            dist_km, duration_sec, _ = GoogleMapsService.get_trip_metrics(p_lat, p_lng, d_lat, d_lng)
            
            # 2. Calculate dynamic courier fare
            ledger = CourierFareCalculator.compute_final_fare(
                distance_km=dist_km, 
                vehicle_type_id=vehicle_type_id,
                category_id=category_id,
                weight_tier_id=weight_tier_id,
                lat=p_lat,
                lng=p_lng
            )
            
            return Response({
                "estimated_fare": ledger['total_fare'],
                "distance_km": round(dist_km, 2),
                "duration_seconds": int(duration_sec),
                "duration_text": f"{int(duration_sec // 60)} mins",
                "distance_text": f"{round(dist_km, 1)} km",
                "currency": "GHS",
                "breakdown": ledger
            })
        except (TypeError, ValueError, AttributeError) as e:
            return Response({"error": f"Invalid parameters: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post', 'patch'])
    def status(self, request, pk=None):
        delivery = self.get_object()
        new_status = request.data.get('status')
        if new_status in [choice[0] for choice in Delivery.STATUS_CHOICES]:
            delivery.status = new_status
            delivery.save()
            
            # Broadcast status update
            self._broadcast_delivery_update(delivery, 'status_update')

            # Send push notification to passenger
            try:
                from notification.utils import send_notification
                if new_status == 'AT_PICKUP':
                    send_notification(
                        user=delivery.passenger,
                        title="📦 Courier Arrived!",
                        body=f"{delivery.driver.full_name if (delivery.driver and delivery.driver.full_name) else 'Your courier'} has arrived at the pickup location.",
                        type='PUSH',
                        ref_id=str(delivery.id),
                        android_channel_id='high_priority_rides',
                        android_sound='horn',
                        ios_sound='horn.wav',
                        extra_data={'notification_type': 'DELIVERY_ACTIVE'},
                        save_in_db=False
                    )
            except Exception as e:
                print(f"Error sending delivery status push notification: {e}")
            
            return Response(DeliverySerializer(delivery).data)
        return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        delivery = self.get_object()
        if delivery.status != 'PENDING':
            return Response({"error": "Delivery already accepted or processed"}, status=status.HTTP_400_BAD_REQUEST)
        
        if request.user.role != 'driver':
            return Response({"error": "Only drivers can accept deliveries"}, status=status.HTTP_403_FORBIDDEN)
            
        profile = getattr(request.user, 'profile', None)
        if not profile:
            from profiles.models import Profile
            profile, _ = Profile.objects.get_or_create(user=request.user)
            
        delivery.driver = profile
        delivery.status = 'ACCEPTED'
        delivery.save()

        # Broadcast acceptance update to subscriber tracking group
        self._broadcast_delivery_update(delivery, 'status_update')

        # Broadcast removal to discovery stream
        self._broadcast_discovery('delivery_taken', {'delivery_id': str(delivery.id)})

        # Send push notification to passenger
        try:
            from notification.utils import send_notification
            send_notification(
                user=delivery.passenger,
                title="📦 Courier Assigned!",
                body=f"{request.user.profile.full_name or 'A courier'} has accepted your delivery request.",
                type='PUSH',
                ref_id=str(delivery.id),
                extra_data={'notification_type': 'DELIVERY_ACTIVE'},
                save_in_db=False
            )
        except Exception as e:
            print(f"Error sending delivery accept push notification: {e}")

        return Response(DeliverySerializer(delivery).data)

    @action(detail=True, methods=['post'])
    def upload_proof(self, request, pk=None):
        """
        Uploads delivery proof (signature, coordinates, photo) and advances delivery status.
        """
        delivery = self.get_object()
        proof_type = request.data.get('proof_type') # 'PICKUP' or 'DROPOFF'
        image_url = request.data.get('image_url')
        signature_base64 = request.data.get('signature_base64')
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        
        if not proof_type or proof_type not in ['PICKUP', 'DROPOFF']:
            return Response({"error": "Invalid proof_type. Must be PICKUP or DROPOFF."}, status=status.HTTP_400_BAD_REQUEST)
            
        if lat is None or lng is None:
            return Response({"error": "Latitude and longitude coordinates are required for verification."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            return Response({"error": "Invalid coordinates format."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Create the proof record
        from .models import DeliveryProof
        proof = DeliveryProof.objects.create(
            delivery=delivery,
            proof_type=proof_type,
            image_url=image_url,
            signature_base64=signature_base64,
            latitude=lat,
            longitude=lng
        )
        
        # Advance state
        if proof_type == 'PICKUP':
            delivery.status = 'PACKAGE_COLLECTED'
        else: # DROPOFF
            delivery.status = 'DELIVERED'
            if image_url:
                delivery.proof_photo_url = image_url
                
        delivery.save()
        
        # Broadcast status update
        self._broadcast_delivery_update(delivery, 'status_update')

        # Send push notification to passenger
        try:
            from notification.utils import send_notification
            status_msgs = {
                'PACKAGE_COLLECTED': "Your package has been picked up by the courier.",
                'DELIVERED': "Your package has been delivered successfully!"
            }
            body_msg = status_msgs.get(delivery.status, f"Delivery status updated to {delivery.status}")
            save_in_db = (delivery.status == 'DELIVERED')
            send_notification(
                user=delivery.passenger,
                title="📦 Delivery Update",
                body=body_msg,
                type='PUSH',
                ref_id=str(delivery.id),
                extra_data={'notification_type': 'DELIVERY_ACTIVE'},
                save_in_db=save_in_db
            )
        except Exception as e:
            print(f"Error sending delivery proof push notification: {e}")
        
        return Response({
            "message": f"Proof uploaded successfully. Delivery advanced to {delivery.status}.",
            "delivery": DeliverySerializer(delivery).data
        })

    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Returns all deliveries that are currently PENDING and available for drivers to accept.
        Filters based on proximity (15km radius) if driver location is provided.
        """
        self._check_and_expire_deliveries()
        user = request.user
        
        has_restricted_vehicle = False
        is_delivery_geofenced = False
        allowed_areas = []
        if hasattr(user, 'profile'):
            from core_settings.models import VehicleCategory
            restricted_slugs = list(VehicleCategory.objects.filter(is_passenger_allowed=False).values_list('slug', flat=True))
            has_restricted_vehicle = user.profile.vehicles.filter(type__in=restricted_slugs, is_active=True).exists()
            
            active_vehicle = user.profile.vehicles.filter(is_active=True).first()
            if active_vehicle:
                try:
                    category = VehicleCategory.objects.get(slug=active_vehicle.type)
                    if category.is_delivery_geofenced:
                        is_delivery_geofenced = True
                        allowed_areas = list(category.allowed_service_areas.all())
                except VehicleCategory.DoesNotExist:
                    pass

        if user.role != 'driver' or not hasattr(user, 'profile') or (not user.profile.receive_deliveries and not has_restricted_vehicle):
            return Response([]) # Only opted-in drivers or restricted vehicle drivers see available deliveries

        driver_lat = user.profile.last_lat
        driver_lng = user.profile.last_lng

        available_deliveries = Delivery.objects.select_related('passenger', 'driver').prefetch_related('proofs').filter(status='PENDING').order_by('-created_at')
        
        filtered_deliveries = []
        
        from django.contrib.gis.geos import Point
        
        for delivery in available_deliveries:
            # 1. Proximity check
            if driver_lat and driver_lng:
                dist = GeospatialUtils.calculate_haversine_distance(driver_lat, driver_lng, delivery.pickup_lat, delivery.pickup_lng) / 1000.0
                if dist > 15.0:
                    continue
            
            # 2. Geofence check
            if is_delivery_geofenced:
                pickup_point = Point(float(delivery.pickup_lng), float(delivery.pickup_lat), srid=4326) if delivery.pickup_lat and delivery.pickup_lng else None
                dropoff_point = Point(float(delivery.dropoff_lng), float(delivery.dropoff_lat), srid=4326) if delivery.dropoff_lat and delivery.dropoff_lng else None
                
                if not pickup_point or not dropoff_point or not allowed_areas:
                    continue
                    
                pickup_in = any(area.polygon.contains(pickup_point) for area in allowed_areas)
                dropoff_in = any(area.polygon.contains(dropoff_point) for area in allowed_areas)
                
                if not (pickup_in and dropoff_in):
                    continue
                    
            filtered_deliveries.append(delivery)

        serializer = DeliverySerializer(filtered_deliveries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        Returns the history of deliveries for the authenticated user (passenger or driver).
        """
        user = request.user
        qs = Delivery.objects.select_related('passenger', 'driver').prefetch_related('proofs')
        if user.role == 'driver':
            queryset = qs.filter(driver=user.profile)
        else:
            queryset = qs.filter(passenger=user)
        
        # Exclude currently active/pending ones for 'history' if desired, 
        # but matching queryset for consistency now.
        serializer = DeliverySerializer(queryset.order_by('-created_at'), many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """
        Nearby delivery discovery with radius filter.
        """
        return self.available(request)
