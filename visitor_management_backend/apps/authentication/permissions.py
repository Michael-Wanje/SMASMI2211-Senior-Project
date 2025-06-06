from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access the view.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'ADMIN' and
            request.user.is_approved
        )

class IsResidentUser(permissions.BasePermission):
    """
    Custom permission to only allow resident users to access the view.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'RESIDENT' and
            request.user.is_approved
        )

class IsSecurityUser(permissions.BasePermission):
    """
    Custom permission to only allow security users to access the view.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'SECURITY' and
            request.user.is_approved
        )

class IsApprovedUser(permissions.BasePermission):
    """
    Custom permission to only allow approved users to access the view.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_approved
        )

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so I'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        return obj.user == request.user

class IsAdminOrResident(permissions.BasePermission):
    """
    Custom permission for admin or resident users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['ADMIN', 'RESIDENT'] and
            request.user.is_approved
        )

class IsAdminOrSecurity(permissions.BasePermission):
    """
    Custom permission for admin or security users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['ADMIN', 'SECURITY'] and
            request.user.is_approved
        )

class CanManageVisitors(permissions.BasePermission):
    """
    Custom permission for users who can manage visitors (Admin, Resident, Security).
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['ADMIN', 'RESIDENT', 'SECURITY'] and
            request.user.is_approved
        )