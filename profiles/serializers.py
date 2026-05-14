from rest_framework import serializers
from .models import Profile, DriverVerification


class DriverVerificationSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='driver_id')

    class Meta:
        model = DriverVerification
        fields = '__all__'


class ProfileSerializer(serializers.ModelSerializer):
    verification = DriverVerificationSerializer(read_only=True)
    email = serializers.ReadOnlyField(source='user.email')
    role = serializers.ReadOnlyField(source='user.role')
    user_id = serializers.ReadOnlyField(source='user.id')
    # Use SerializerMethodField to ensure absolute URLs regardless of request context
    profile_picture = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()

    def get_profile_picture(self, obj):
        if not obj.profile_picture:
            return None
        # Handle relative paths for Flutter compatibility
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.profile_picture.url)
        return f"https://api.flexyridegh.com{obj.profile_picture.url}"

    def get_photo_url(self, obj):
        return self.get_profile_picture(obj)

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
            # Safer check for OneToOne relation to avoid RelatedObjectDoesNotExist
            verification = getattr(obj, 'verification', None)
            return bool(verification.is_verified) if verification else False
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in get_is_verified: {e}")
            return False

    def get_is_subscribed(self, obj):
        """True only when the driver has an active subscription."""
        try:
            if not hasattr(obj, 'user') or obj.user.role != 'driver':
                return False
            
            # Check for the DriverSubscription relation
            subscription = getattr(obj, 'subscription', None)
            if not subscription:
                return False
                
            return bool(subscription.is_currently_active)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in get_is_subscribed: {e}")
            return False

    def get_rating_count(self, obj):
        """Placeholder until the ratings module exposes a per-driver count."""
        return 0
