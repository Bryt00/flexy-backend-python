import requests
import jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

class SocialAuthService:
    @staticmethod
    def verify_google_token(token):
        """
        Verify a Google ID token and return user info.
        """
        try:
            # We check both the web and mobile client IDs if provided
            client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
            
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                client_id
            )

            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise AuthenticationFailed('Wrong issuer.')

            return {
                'email': idinfo.get('email'),
                'social_id': idinfo.get('sub'),
                'first_name': idinfo.get('given_name', ''),
                'last_name': idinfo.get('family_name', ''),
                'picture': idinfo.get('picture', '')
            }
        except Exception as e:
            raise AuthenticationFailed(f'Invalid Google token: {str(e)}')

    @staticmethod
    def verify_apple_token(token):
        """
        Verify an Apple ID token and return user info.
        """
        try:
            # 1. Fetch Apple's public keys
            apple_keys_url = "https://appleid.apple.com/auth/keys"
            jwks = requests.get(apple_keys_url).json()
            
            # 2. Decode the token header to find the kid (Key ID)
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            # 3. Find the matching public key
            public_key = None
            for key in jwks['keys']:
                if key['kid'] == kid:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break
            
            if not public_key:
                raise AuthenticationFailed('Apple public key not found.')

            # 4. Verify and decode the JWT
            # For Apple, audience is the App Bundle ID
            client_id = getattr(settings, 'APPLE_OAUTH_CLIENT_ID', None)
            
            decoded = jwt.decode(
                token,
                public_key,
                audience=client_id,
                algorithms=['RS256']
            )

            return {
                'email': decoded.get('email'),
                'social_id': decoded.get('sub'), # Unique user ID for Apple
            }
        except Exception as e:
            raise AuthenticationFailed(f'Invalid Apple token: {str(e)}')
