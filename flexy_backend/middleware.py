from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from urllib.parse import parse_qs

User = get_user_model()

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class QueryAuthMiddleware:
    """
    Custom middleware that populates scope['user'] from a JWT in the query string.
    Expected key is 'token'.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        token_key = query_params.get('token')

        if token_key:
            try:
                token = token_key[0]
                access_token = AccessToken(token)
                
                # Support both 'user_id' and 'sub' claims
                user_id = access_token.get('user_id') or access_token.get('sub')
                
                if user_id:
                    scope['user'] = await get_user(user_id)
                    if scope['user'].is_anonymous:
                        print(f"QueryAuthMiddleware: User ID {user_id} not found in database.")
                else:
                    print("QueryAuthMiddleware: No user_id or sub claim found in token.")
                    scope['user'] = AnonymousUser()
            except Exception as e:
                print(f"QueryAuthMiddleware: Token validation failed: {str(e)}")
                scope['user'] = AnonymousUser()
        else:
            print("QueryAuthMiddleware: No token found in query parameters.")
            scope['user'] = AnonymousUser()

        return await self.inner(scope, receive, send)
