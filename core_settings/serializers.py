from rest_framework import serializers
from .models import SiteSetting

class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = ['key', 'value']

from .models import DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType, VehicleCategory, ServiceArea
import json

class ServiceAreaSerializer(serializers.ModelSerializer):
    polygon = serializers.SerializerMethodField()

    class Meta:
        model = ServiceArea
        fields = ['id', 'name', 'polygon', 'is_active']

    def get_polygon(self, obj):
        if obj.polygon:
            return json.loads(obj.polygon.geojson)
        return None

class DeliveryCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryCategory
        fields = '__all__'

class DeliveryWeightTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryWeightTier
        fields = '__all__'

class DeliveryVehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryVehicleType
        fields = '__all__'

class VehicleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleCategory
        fields = '__all__'
