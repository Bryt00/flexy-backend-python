from drf_spectacular.extensions import OpenApiAuthenticationExtension
from .authentication import APIKeyAuthentication

class APIKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = APIKeyAuthentication
    name = 'ApiKeyAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-Api-Key',
            'description': 'API Key Authentication. Example: fx_prefix_secret'
        }
