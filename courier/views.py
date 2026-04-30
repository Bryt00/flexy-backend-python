from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Delivery
from .serializers import DeliverySerializer
from rides.utils import FareCalculator
from integrations.google_maps import GoogleMapsService

class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Passengers see their requested deliveries, drivers see assigned ones
        user = self.request.user
        if user.role == 'driver':
            return Delivery.objects.filter(driver=user.profile)
        return Delivery.objects.filter(passenger=user)

    def perform_create(self, serializer):
        delivery = serializer.save(passenger=self.request.user)
        
        # Broadcast to available drivers (Discovery stream)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'delivery_discovery',
            {
                'type': 'delivery_broadcast',
                'message_type': 'new_delivery',
                'data': DeliverySerializer(delivery).data
            }
        )

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
            # item_category and weight are available but we use distance-based pricing for now
            
            # 1. Fetch real metrics from Google
            dist_km, duration_sec = GoogleMapsService.get_trip_metrics(p_lat, p_lng, d_lat, d_lng)
            
            # 2. Calculate fare using 'motorbike' as the baseline for delivery
            ledger = FareCalculator.compute_final_fare(dist_km, 'motorbike')
            
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
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'delivery_{delivery.id}',
                {
                    'type': 'delivery_broadcast',
                    'message_type': 'status_update',
                    'data': DeliverySerializer(delivery).data
                }
            )
            
            return Response(DeliverySerializer(delivery).data)
        return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        delivery = self.get_object()
        if delivery.status != 'PENDING':
            return Response({"error": "Delivery already accepted or processed"}, status=status.HTTP_400_BAD_REQUEST)
        
        if request.user.role != 'driver':
            return Response({"error": "Only drivers can accept deliveries"}, status=status.HTTP_403_FORBIDDEN)
            
        delivery.driver = request.user.profile
        delivery.status = 'ACCEPTED'
        delivery.save()

        # Broadcast acceptance update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'delivery_{delivery.id}',
            {
                'type': 'delivery_broadcast',
                'message_type': 'status_update',
                'data': DeliverySerializer(delivery).data
            }
        )

        return Response(DeliverySerializer(delivery).data)

    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Returns all deliveries that are currently PENDING and available for drivers to accept.
        """
        # In the future, we can filter by proximity here.
        available_deliveries = Delivery.objects.filter(status='PENDING').order_by('-created_at')
        serializer = DeliverySerializer(available_deliveries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        Returns the history of deliveries for the authenticated user (passenger or driver).
        """
        user = request.user
        if user.role == 'driver':
            queryset = Delivery.objects.filter(driver=user.profile)
        else:
            queryset = Delivery.objects.filter(passenger=user)
        
        # Exclude currently active/pending ones for 'history' if desired, 
        # but matching queryset for consistency now.
        serializer = DeliverySerializer(queryset.order_by('-created_at'), many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """
        Stub for nearby delivery discovery (GPR/Radius).
        """
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        # radius_km = float(request.query_params.get('radius', 5.0))
        
        # For now, just return available ones as a fallback
        return self.available(request)
