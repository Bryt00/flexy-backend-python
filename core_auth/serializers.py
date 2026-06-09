from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import DeletionRequest

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'role', 'phone', 'is_email_verified', 'google_id', 'apple_id', 'created_at')
        read_only_fields = ('id', 'created_at', 'phone', 'is_email_verified')

    def get_phone(self, obj):
        try:
            return obj.profile.phone_number
        except AttributeError:
            return None
        except Exception:
            return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'role', 'referral_code')

    def validate_role(self, value):
        # Normalize role: 'passenger' or 'Passenger' -> 'rider'
        # ensure it matches the keys in User.ROLE_CHOICES
        value = value.lower()
        if value == 'passenger':
            return 'rider'

        # Check if the value is a valid choice key
        valid_choices = [choice[0] for choice in User.ROLE_CHOICES]
        if value not in valid_choices:
            raise serializers.ValidationError(f"Invalid role. Choose from: {', '.join(valid_choices)}")

        return value

    def validate_referral_code(self, value):
        if value:
            from profiles.models import Profile
            if not Profile.objects.filter(referral_code=value).exists():
                raise serializers.ValidationError("Invalid referral code. Please check for typos.")
        return value

    def create(self, validated_data):
        referral_code = validated_data.pop('referral_code', None)
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'rider'),
            is_active=False  # Deactivate until email is verified
        )

        # Create Profile immediately to handle referral logic
        from profiles.models import Profile
        profile = Profile.objects.create(user=user)

        if referral_code:
            try:
                referrer_profile = Profile.objects.get(referral_code=referral_code)
                profile.referred_by = referrer_profile
                profile.save()

                # --- DOUBLE-SIDED WELCOME REWARD ---
                # Instantly generate a WELCOME promo code for the referee
                import random
                from rides.models import PromoCode
                from django.utils import timezone
                from datetime import timedelta

                welcome_code_str = f"WELCOME-{referrer_profile.referral_code}-{random.randint(100, 999)}"
                PromoCode.objects.create(
                    user=user,
                    code=welcome_code_str,
                    type='fixed',
                    value=5.0,
                    usage_limit=1,
                    expires_at=timezone.now() + timedelta(days=30),
                    active=True
                )

                # Try sending push notification for welcome reward
                try:
                    from notification.utils import send_notification
                    send_notification(
                        user,
                        title="Welcome Bonus! 🎁",
                        body=f"Enjoy GH₵ 5.00 off your first ride with promo code {welcome_code_str}.",
                        type='PUSH'
                    )
                except Exception:
                    pass

            except Profile.DoesNotExist:
                pass  # Already handled by validate_referral_code, but keep try-except to be absolutely safe

        return user


class DeletionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeletionRequest
        fields = '__all__'
        read_only_fields = ('id', 'user', 'requested_at', 'processed_at')


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class TokenResponseSerializer(serializers.Serializer):
    user = UserSerializer()
    token = serializers.CharField()
    refresh_token = serializers.CharField()


class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    type = serializers.ChoiceField(choices=['email_verification', 'password_reset'])


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()
    type = serializers.ChoiceField(choices=['email_verification', 'password_reset'])


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()
    new_password = serializers.CharField(write_only=True)


class RefreshTokenRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class RefreshTokenResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    refresh_token = serializers.CharField()


class SocialAuthSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'apple'])
    token = serializers.CharField()
    role = serializers.CharField(required=False, default='rider')
