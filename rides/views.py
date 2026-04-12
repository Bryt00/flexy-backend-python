from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Ride, ChatMessage, Incident
from .serializers import RideSerializer, ChatMessageSerializer, IncidentSerializer

from .tasks import process_ride_matching
from payments.tasks import process_ride_earnings

class RideViewSet(viewsets.ModelViewSet):
    queryset = Ride.objects.all()
    serializer_class = RideSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        ride = serializer.save(rider=self.request.user)
        # Trigger matching service in background
        process_ride_matching.delay(ride.id)

    @action(detail=True, methods=['post', 'put', 'patch'])
    def status(self, request, pk=None):
        ride = self.get_object()
        new_status = request.data.get('status')
        if new_status in [choice[0] for choice in Ride.STATUS_CHOICES]:
            ride.status = new_status
            ride.save()
            
            # If completed, trigger earnings processing
            if new_status == 'completed' and ride.driver:
                process_ride_earnings.delay(
                    ride.driver.user.id,
                    ride.fare or 0,
                    ride.id
                )
            return Response(self.get_serializer(ride).data)
        return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        ride = self.get_object()
        if ride.status != 'pending':
            return Response({"error": "Ride already accepted or cancelled"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Profile check for driver
        if not hasattr(request.user, 'profile'):
             return Response({"error": "User has no profile"}, status=status.HTTP_400_BAD_REQUEST)
             
        ride.driver = request.user.profile
        ride.status = 'accepted'
        ride.save()
        return Response(self.get_serializer(ride).data)

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

    @action(detail=True, methods=['get'])
    def chat_history(self, request, pk=None):
        ride = self.get_object()
        messages = ride.messages.all().order_by('created_at')
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)
