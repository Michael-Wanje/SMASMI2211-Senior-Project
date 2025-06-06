from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

User = get_user_model()

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'user_type', 'approval_status', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_approved', 'is_active', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number', 'apartment_number')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('email', 'first_name', 'last_name', 'phone_number')
        }),
        ('User Type & Location', {
            'fields': ('user_type', 'apartment_number', 'building_name', 'address')
        }),
        ('Account Status', {
            'fields': ('is_active', 'is_approved', 'is_staff', 'is_superuser')
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_users', 'disapprove_users', 'activate_users', 'deactivate_users']
    
    def full_name(self, obj):
        return obj.get_full_name()
    full_name.short_description = 'Full Name'
    
    def approval_status(self, obj):
        if obj.is_approved:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Approved</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Pending</span>'
            )
    approval_status.short_description = 'Approval Status'
    
    def approve_users(self, request, queryset):
        updated = 0
        for user in queryset:
            if not user.is_approved:
                user.is_approved = True
                user._approval_status_changed = True
                user.save()
                updated += 1
        
        self.message_user(request, f'{updated} users approved successfully.')
    approve_users.short_description = "Approve selected users"
    
    def disapprove_users(self, request, queryset):
        updated = 0
        for user in queryset:
            if user.is_approved and user.user_type != 'ADMIN':
                user.is_approved = False
                user._approval_status_changed = True
                user.save()
                updated += 1
        
        self.message_user(request, f'{updated} users disapproved successfully.')
    disapprove_users.short_description = "Disapprove selected users"
    
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users activated successfully.')
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        # Don't deactivate superusers
        queryset = queryset.exclude(is_superuser=True)
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users deactivated successfully.')
    deactivate_users.short_description = "Deactivate selected users"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of superusers
        if obj and obj.is_superuser:
            return False
        return super().has_delete_permission(request, obj)