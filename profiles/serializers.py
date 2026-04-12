from rest_framework import serializers
from .models import Profile, DriverVerification

class DriverVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverVerification
        fields = '__all__'

class ProfileSerializer(serializers.ModelSerializer):
    verification = DriverVerificationSerializer(read_only=True)
    email = serializers.ReadOnlyField(source='user.email')

    class Meta:
        model = Profile
        fields = ('user', 'email', 'full_name', 'phone_number', 'profile_picture_url', 'rating', 'verification', 'created_at')
        read_only_fields = ('user', 'created_at', 'rating')
