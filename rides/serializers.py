from rest_framework import serializers
from .models import Ride, Incident, ChatMessage, FavoriteLocation, Rating, RideStop, PromoCode
from core_auth.serializers import UserSerializer

class RideStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideStop
        fields = '__all__'

class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = '__all__'

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_type = serializers.SerializerMethodField()
    ride_id = serializers.CharField(source='ride.id', read_only=True)
    sender_id = serializers.CharField(source='sender.id', read_only=True)
    timestamp = serializers.DateTimeField(source='created_at', read_only=True, format='%Y-%m-%dT%H:%M:%S.%fZ')

    class Meta:
        model = ChatMessage
        fields = ('id', 'ride_id', 'sender_id', 'sender_type', 'content', 'timestamp', 'is_quick_message')
        read_only_fields = ('id', 'timestamp')

    def get_sender_type(self, obj):
        # We assume 'rider' if they are the rider of the linked ride, else 'driver'
        # Or check user role.
        if obj.sender.role == 'driver':
            return 'driver'
        return 'rider'

class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = '__all__'

class FavoriteLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteLocation
        fields = '__all__'
        read_only_fields = ('id', 'user', 'created_at')

class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = '__all__'

class RideSerializer(serializers.ModelSerializer):
    rider_details = UserSerializer(source='rider', read_only=True)
    incidents = IncidentSerializer(many=True, read_only=True)
    stops = RideStopSerializer(many=True, read_only=True)
    
    # Unified IDs for Flutter — UUIDField ensures serialization to string
    rider_id = serializers.UUIDField(source='rider.id', read_only=True)
    driver_id = serializers.UUIDField(source='driver.id', read_only=True, allow_null=True)
    
    # Enriched Fields (Flattened for App Consumption)
    driver_name = serializers.SerializerMethodField()
    driver_photo = serializers.SerializerMethodField()
    driver_phone = serializers.SerializerMethodField()
    vehicle_info = serializers.SerializerMethodField()
    driver_lat = serializers.SerializerMethodField()
    driver_lng = serializers.SerializerMethodField()
    
    # Rider Fallbacks (If not explicitly set on Ride model)
    rider_name = serializers.SerializerMethodField()
    rider_photo = serializers.SerializerMethodField()
    rider_phone = serializers.SerializerMethodField()
    
    class Meta:
        model = Ride
        fields = '__all__'
        read_only_fields = ('id', 'rider', 'driver', 'status', 'created_at', 'updated_at')

    def get_driver_name(self, obj):
        if obj.driver and hasattr(obj.driver, 'profile'):
            return obj.driver.profile.full_name
        return None

    def get_driver_photo(self, obj):
        if obj.driver and hasattr(obj.driver, 'profile'):
            pic = obj.driver.profile.profile_picture
            return pic.url if pic else None
        return None

    def get_driver_phone(self, obj):
        if obj.driver and hasattr(obj.driver, 'profile'):
            return obj.driver.profile.phone_number
        return None

    def get_vehicle_info(self, obj):
        if obj.driver and hasattr(obj.driver, 'profile'):
            # Fetch most recent/active vehicle
            vehicle = obj.driver.profile.vehicles.filter(is_active=True).first()
            if vehicle:
                return f"{vehicle.color} {vehicle.make} {vehicle.model} ({vehicle.license_plate})"
        return "Standard Vehicle"

    def get_driver_lat(self, obj):
        if obj.driver and hasattr(obj.driver, 'profile'):
            return obj.driver.profile.last_lat
        return None

    def get_driver_lng(self, obj):
        if obj.driver and hasattr(obj.driver, 'profile'):
            return obj.driver.profile.last_lng
        return None

    def get_rider_name(self, obj):
        return obj.rider_name or (obj.rider.profile.full_name if obj.rider and hasattr(obj.rider, 'profile') else None)

    def get_rider_photo(self, obj):
        if obj.rider_photo:
            return obj.rider_photo
        if obj.rider and hasattr(obj.rider, 'profile'):
            pic = obj.rider.profile.profile_picture
            return pic.url if pic else None
        return None

    def get_rider_phone(self, obj):
        return obj.rider_phone or (obj.rider.profile.phone_number if obj.rider and hasattr(obj.rider, 'profile') else None)
