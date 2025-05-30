from django.contrib import admin
from .models import Visitor, VisitorLog

class VisitorLogInline(admin.TabularInline):
    model = VisitorLog
    extra = 0
    readonly_fields = ('timestamp',)

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'resident', 'visit_date', 'status', 'purpose', 'created_at')
    list_filter = ('status', 'purpose', 'visit_date', 'created_at')
    search_fields = ('full_name', 'phone_number', 'email', 'resident__user__email')
    readonly_fields = ('created_at', 'updated_at', 'checked_in_at', 'checked_out_at', 'approved_at')
    inlines = [VisitorLogInline]
    
    fieldsets = (
        ('Visitor Information', {
            'fields': ('full_name', 'phone_number', 'email', 'id_number', 'company')
        }),
        ('Visit Details', {
            'fields': ('resident', 'purpose', 'visit_date', 'visit_time', 
                      'expected_duration', 'number_of_visitors', 'additional_notes')
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approved_at')
        }),
        ('Check In/Out', {
            'fields': ('checked_in_at', 'checked_out_at', 'checked_in_by')
        }),
        ('System Fields', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    list_display = ('visitor', 'action', 'performed_by', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('visitor__full_name', 'performed_by__email')
    readonly_fields = ('timestamp',)