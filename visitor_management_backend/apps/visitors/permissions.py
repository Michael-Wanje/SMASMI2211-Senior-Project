from rest_framework import permissions

class IsResidentOrSecurity(permissions.BasePermission):
    """
    Custom permission to only allow residents or security personnel to access certain views.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['resident', 'security']
        )

class IsSecurityOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow security personnel or admin to access certain views.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['security', 'admin']
        )

class IsResidentOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow residents or admin to access certain views.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['resident', 'admin']
        )

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        return obj.resident == request.user

class IsVisitorOwner(permissions.BasePermission):
    """
    Custom permission to check if user is the visitor owner or has appropriate role.
    """
    
    def has_object_permission(self, request, view, obj):
        # Allow admins full access
        if request.user.user_type == 'admin':
            return True
        
        # Allow security personnel to view and update
        if request.user.user_type == 'security':
            return request.method in ['GET', 'PUT', 'PATCH']
        
        # Allow residents to view their own visit requests
        if request.user.user_type == 'resident':
            return obj.resident == request.user
        
        return False