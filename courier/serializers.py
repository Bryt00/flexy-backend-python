from rest_framework import serializers
from .models import Delivery, DeliveryProof
from core_auth.serializers import UserSerializer

class DeliveryProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryProof
        fields = '__all__'

class DeliverySerializer(serializers.ModelSerializer):
    passenger_details = UserSerializer(source='passenger', read_only=True)
    driver_name = serializers.SerializerMethodField()
    driver_photo = serializers.SerializerMethodField()
    driver_vehicle_info = serializers.SerializerMethodField()
    driver_license_plate = serializers.SerializerMethodField()
    item_category_name = serializers.CharField(source='item_category.name', read_only=True, allow_null=True)
    weight_tier_name = serializers.CharField(source='weight_tier.name', read_only=True, allow_null=True)
    vehicle_type_name = serializers.CharField(source='vehicle_type.name', read_only=True, allow_null=True)
    proofs = DeliveryProofSerializer(many=True, read_only=True)

    class Meta:
        model = Delivery
        fields = '__all__'
        read_only_fields = ('id', 'passenger', 'driver', 'status', 'created_at', 'updated_at')

    def get_driver_name(self, obj):
        if obj.driver:
            return obj.driver.full_name
        return None

    def get_driver_photo(self, obj):
        if obj.driver and obj.driver.profile_picture:
            return obj.driver.profile_picture.url
        return None

    def get_driver_vehicle_info(self, obj):
        if obj.driver:
            vehicle = obj.driver.vehicles.filter(is_active=True).first()
            if vehicle:
                return f"{vehicle.make or ''} {vehicle.model or ''}".strip()
        return None

    def get_driver_license_plate(self, obj):
        if obj.driver:
            vehicle = obj.driver.vehicles.filter(is_active=True).first()
            if vehicle:
                return vehicle.license_plate
        return None
