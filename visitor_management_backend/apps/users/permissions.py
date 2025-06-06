from rest_framework import permissions

class CanManageUsers(permissions.BasePermission):
    """
    Custom permission for user management operations.
    Only admin users can manage other users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'ADMIN' and
            request.user.is_approved
        )

class CanViewUsers(permissions.BasePermission):
    """
    Custom permission for viewing user lists.
    Admin and security can view users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['ADMIN', 'SECURITY'] and
            request.user.is_approved
        )

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow users to edit their own profile or admin to edit any profile.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access any user profile
        if request.user.user_type == 'ADMIN':
            return True
        
        # Users can only access their own profile
        return obj == request.user

class CanApproveUsers(permissions.BasePermission):
    """
    Custom permission for user approval operations.
    Only admin users can approve/disapprove other users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'ADMIN' and
            request.user.is_approved
        )

    def has_object_permission(self, request, view, obj):
        # Cannot approve/disapprove admin users
        if obj.user_type == 'ADMIN':
            return False
        
        # Cannot approve/disapprove self
        if obj == request.user:
            return False
        
        return True