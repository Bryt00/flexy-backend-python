from rest_framework import serializers
from .models import SiteSetting

class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = ['key', 'value']

from .models import DeliveryCategory, DeliveryWeightTier, DeliveryVehicleType

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
