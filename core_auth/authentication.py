from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        
        token_session_key = validated_token.get('session_key')
        if not token_session_key:
            raise AuthenticationFailed('Token does not contain a session_key', code='session_key_missing')
            
        if str(user.session_key) != token_session_key:
            raise AuthenticationFailed('Session expired. You logged in on another device.', code='session_expired')
            
        return user
