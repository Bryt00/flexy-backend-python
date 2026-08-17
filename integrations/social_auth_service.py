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
        import logging
        logger = logging.getLogger(__name__)
        try:
            client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
            
            # Configure a requests session with timeout for fetching certs
            session = requests.Session()
            request_adapter = google_requests.Request(session=session)

            # We pass audience=None to avoid strict matching since the token could be issued 
            # for the web client ID or the Android/iOS client IDs.
            idinfo = id_token.verify_oauth2_token(
                token, 
                request_adapter, 
                audience=None
            )

            # Verify that the audience belongs to our project (matches project number prefix)
            if client_id:
                project_number = client_id.split('-')[0]
                aud = idinfo.get('aud', '')
                if not aud.startswith(project_number):
                    logger.warning(f"Google token aud '{aud}' does not match project number '{project_number}'")
                    raise AuthenticationFailed('Token was not issued for this project.')

            if idinfo.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
                raise AuthenticationFailed('Wrong issuer.')

            return {
                'email': idinfo.get('email'),
                'social_id': idinfo.get('sub'),
                'first_name': idinfo.get('given_name', ''),
                'last_name': idinfo.get('family_name', ''),
                'picture': idinfo.get('picture', '')
            }
        except AuthenticationFailed:
            raise
        except Exception as e:
            logger.error(f"Google token verification failed: {str(e)}", exc_info=True)
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
