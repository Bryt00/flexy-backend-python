from rest_framework import permissions

class IsDeveloperOrAdmin(permissions.BasePermission):
    """
    Permission class allowing access to users with role='developer',
    role='admin', role='super_admin', or is_staff=True.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', '')
        return (
            request.user.is_staff or 
            request.user.is_superuser or 
            user_role in ['developer', 'admin', 'super_admin']
        )
