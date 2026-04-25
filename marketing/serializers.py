from rest_framework import serializers
from .models import Campaign, PromoCode

class CampaignSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = Campaign
        fields = ('id', 'title', 'description', 'image_url', 'target_url', 'status', 'is_active', 'start_date', 'end_date')

class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = '__all__'
