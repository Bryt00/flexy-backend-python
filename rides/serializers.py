from rest_framework import serializers
from .models import Ride, Incident, ChatMessage
from core_auth.serializers import UserSerializer

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.ReadOnlyField(source='sender.email')
    
    class Meta:
        model = ChatMessage
        fields = ('id', 'ride', 'sender', 'sender_email', 'content', 'is_quick_message', 'created_at')
        read_only_fields = ('id', 'created_at')

class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = '__all__'

class RideSerializer(serializers.ModelSerializer):
    rider_details = UserSerializer(source='rider', read_only=True)
    incidents = IncidentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Ride
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
