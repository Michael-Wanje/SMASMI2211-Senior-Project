from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    """
    Permission class to allow only admin users
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'admin'
        )

class IsResidentUser(BasePermission):
    """
    Permission class to allow only resident users
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'resident' and
            request.user.is_approved
        )

class IsSecurityUser(BasePermission):
    """
    Permission class to allow only security users
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'security'
        )

class IsVisitorUser(BasePermission):
    """
    Permission class to allow only visitor users
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'visitor'
        )

class IsAdminOrResident(BasePermission):
    """
    Permission class to allow admin or resident users
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['admin', 'resident']
        )

class IsSecurityOrAdmin(BasePermission):
    """
    Permission class to allow security or admin users
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['security', 'admin']
        )

class IsResidentOrSecurity(BasePermission):
    """
    Permission class to allow resident or security users
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['resident', 'security']
        )

class IsOwnerOrAdmin(BasePermission):
    """
    Permission class to allow owners of objects or admin users
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Admin users can access any object
        if request.user.user_type == 'admin':
            return True
        
        # Check if user is the owner of the object
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'resident'):
            return obj.resident == request.user
        elif hasattr(obj, 'visitor'):
            return obj.visitor.user == request.user if hasattr(obj.visitor, 'user') else False
        
        return False

class IsApprovedResident(BasePermission):
    """
    Permission class to allow only approved resident users
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'resident' and
            request.user.is_approved == True
        )

class CanManageVisitors(BasePermission):
    """
    Permission class for users who can manage visitors (residents and security)
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['resident', 'security', 'admin']
        )

class CanViewReports(BasePermission):
    """
    Permission class for users who can view reports (security and admin)
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['security', 'admin']
        )

class CanManageResidents(BasePermission):
    """
    Permission class for users who can manage residents (admin only)
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'admin'
        )

class IsVisitRequestOwner(BasePermission):
    """
    Permission class to check if user owns the visit request
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Admin can access any visit request
        if request.user.user_type == 'admin':
            return True
        
        # Resident who received the request
        if request.user.user_type == 'resident' and obj.resident == request.user:
            return True
        
        # Security can view all requests
        if request.user.user_type == 'security':
            return True
        
        # Visitor who made the request (if visitor has user account)
        if (request.user.user_type == 'visitor' and 
            hasattr(obj.visitor, 'user') and 
            obj.visitor.user == request.user):
            return True
        
        return False

class IsNotBlacklisted(BasePermission):
    """
    Permission class to check if visitor is not blacklisted
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        if request.user.user_type == 'visitor':
            # Check if visitor is blacklisted
            try:
                from apps.visitors.models import Visitor
                visitor = Visitor.objects.get(user=request.user)
                return not visitor.is_blacklisted
            except Visitor.DoesNotExist:
                return True
        
        return True

class CanRecordEntry(BasePermission):
    """
    Permission class for users who can record visitor entries (security and admin)
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type in ['security', 'admin']
        )

class CanApproveResidents(BasePermission):
    """
    Permission class for users who can approve residents (admin only)
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'admin' and
            request.user.is_staff
        )