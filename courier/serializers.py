from rest_framework import serializers
from .models import Delivery
from core_auth.serializers import UserSerializer

class DeliverySerializer(serializers.ModelSerializer):
    passenger_details = UserSerializer(source='passenger', read_only=True)
    driver_name = serializers.SerializerMethodField()
    driver_photo = serializers.SerializerMethodField()

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
