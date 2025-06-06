from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Visitor, VisitRequest, BlacklistedVisitor

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone_number', 'email', 'id_number', 'is_blacklisted', 'created_at')
    list_filter = ('is_blacklisted', 'created_at')
    search_fields = ('first_name', 'last_name', 'phone_number', 'email', 'id_number')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone_number', 'email', 'id_number', 'company')
        }),
        ('Status', {
            'fields': ('is_blacklisted',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def full_name(self, obj):
        return obj.get_full_name()
    full_name.short_description = 'Full Name'
    
    actions = ['blacklist_visitors', 'remove_from_blacklist']
    
    def blacklist_visitors(self, request, queryset):
        updated = queryset.update(is_blacklisted=True)
        self.message_user(request, f'{updated} visitors blacklisted successfully.')
    blacklist_visitors.short_description = "Blacklist selected visitors"
    
    def remove_from_blacklist(self, request, queryset):
        updated = queryset.update(is_blacklisted=False)
        self.message_user(request, f'{updated} visitors removed from blacklist successfully.')
    remove_from_blacklist.short_description = "Remove from blacklist"

@admin.register(VisitRequest)
class VisitRequestAdmin(admin.ModelAdmin):
    list_display = ('visitor_name', 'resident_name', 'status_display', 'visit_date', 'visit_time', 'created_at')
    list_filter = ('status', 'visit_date', 'created_at', 'request_type')
    search_fields = ('visitor__first_name', 'visitor__last_name', 'resident__first_name', 'resident__last_name', 'purpose')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'approved_at', 'checked_in_at', 'checked_out_at')
    
    fieldsets = (
        ('Visit Information', {
            'fields': ('visitor', 'resident', 'purpose', 'visit_date', 'visit_time', 'request_type')
        }),
        ('Status', {
            'fields': ('status', 'notes')
        }),
        ('Security Information', {
            'fields': ('approved_by', 'security_officer'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'approved_at', 'checked_in_at', 'checked_out_at'),
            'classes': ('collapse',)
        }),
    )
    
    def visitor_name(self, obj):
        return obj.visitor.get_full_name()
    visitor_name.short_description = 'Visitor'
    
    def resident_name(self, obj):
        return obj.resident.get_full_name()
    resident_name.short_description = 'Resident'
    
    def status_display(self, obj):
        colors = {
            'PENDING': 'orange',
            'APPROVED': 'green',
            'DENIED': 'red',
            'CHECKED_IN': 'blue',
            'CHECKED_OUT': 'gray',
            'EXPIRED': 'darkred'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    actions = ['approve_requests', 'deny_requests']
    
    def approve_requests(self, request, queryset):
        updated = 0
        for visit_request in queryset.filter(status='PENDING'):
            visit_request.status = 'APPROVED'
            visit_request.approved_by = request.user
            visit_request.approved_at = timezone.now()
            visit_request.save()
            updated += 1
        self.message_user(request, f'{updated} visit requests approved successfully.')
    approve_requests.short_description = "Approve selected requests"
    
    def deny_requests(self, request, queryset):
        updated = 0
        for visit_request in queryset.filter(status='PENDING'):
            visit_request.status = 'DENIED'
            visit_request.approved_by = request.user
            visit_request.approved_at = timezone.now()
            visit_request.save()
            updated += 1
        self.message_user(request, f'{updated} visit requests denied successfully.')
    deny_requests.short_description = "Deny selected requests"

@admin.register(BlacklistedVisitor)
class BlacklistedVisitorAdmin(admin.ModelAdmin):
    list_display = ('visitor_name', 'resident_name', 'reason', 'blacklisted_by', 'created_at')
    list_filter = ('created_at', 'blacklisted_by')
    search_fields = ('visitor__first_name', 'visitor__last_name', 'resident__first_name', 'resident__last_name', 'reason')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    def visitor_name(self, obj):
        return obj.visitor.get_full_name()
    visitor_name.short_description = 'Visitor'
    
    def resident_name(self, obj):
        return obj.resident.get_full_name()
    resident_name.short_description = 'Resident'