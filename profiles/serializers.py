from rest_framework import serializers
from .models import Profile, DriverVerification


class DriverVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverVerification
        fields = '__all__'


class ProfileSerializer(serializers.ModelSerializer):
    verification = DriverVerificationSerializer(read_only=True)
    email = serializers.ReadOnlyField(source='user.email')
    role = serializers.ReadOnlyField(source='user.role')
    user_id = serializers.ReadOnlyField(source='user.id')
    # Use ImageField to automatically provide a full URL for the Flutter app
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    photo_url = serializers.ImageField(source='profile_picture', read_only=True)

    # Computed cross-model fields consumed by the Flutter app
    is_verified = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(source='is_online', required=False)
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            'user', 'user_id', 'email', 'role',
            'full_name', 'phone_number', 'city',
            'emergency_name', 'emergency_phone',
            'profile_picture', 'photo_url',
            'rating', 'rating_count',
            'points', 'tier', 'acceptance_rate', 'cancellation_rate', 'total_rides',
            'verification',
            'is_verified', 'is_subscribed', 'is_active', 'is_online',
            'created_at',
        )
        read_only_fields = ('user', 'created_at', 'rating')

    def get_is_verified(self, obj):
        """True only when DriverVerification.is_verified is True."""
        try:
            return bool(obj.verification.is_verified)
        except Exception:
            return False

    def get_is_subscribed(self, obj):
        """True only when the driver has an active subscription."""
        try:
            # Check if current user is a driver first
            if obj.user.role != 'driver':
                return False
            
            # Check for the DriverSubscription relation
            subscription = getattr(obj, 'subscription', None)
            if not subscription:
                return False
                
            return bool(subscription.is_currently_active)
        except Exception:
            return False

    def get_rating_count(self, obj):
        """Placeholder until the ratings module exposes a per-driver count."""
        return 0
