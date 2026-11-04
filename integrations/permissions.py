from rest_framework import permissions
from .models import APIKey

class HasAPIKeyScope(permissions.BasePermission):
    """
    Permission class that checks if the request's API key has the required scope.
    If the request was authenticated using JWT or session auth (e.g. human user in UI),
    normal user permissions apply without scope blocking.
    """
    required_scope = None

    def __init__(self, required_scope=None):
        if required_scope:
            self.required_scope = required_scope

    def has_permission(self, request, view):
        # Allow standard authenticated users (JWT/Session)
        if not hasattr(request, 'auth') or not isinstance(request.auth, APIKey):
            return bool(request.user and request.user.is_authenticated)

        api_key: APIKey = request.auth
        if not api_key.is_active:
            return False

        scope_needed = getattr(view, 'required_scope', self.required_scope)
        if not scope_needed:
            return True

        return api_key.has_scope(scope_needed)


def require_scope(scope_name: str):
    """
    Helper function to dynamically create a HasAPIKeyScope permission class
    with a specific scope.
    """
    class ScopedPermission(HasAPIKeyScope):
        required_scope = scope_name
    return ScopedPermission

