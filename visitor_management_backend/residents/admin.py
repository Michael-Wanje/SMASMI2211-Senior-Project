from django.contrib import admin
from .models import Resident, ResidentContact

class ResidentContactInline(admin.TabularInline):
    model = ResidentContact
    extra = 1

@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ('user', 'apartment_number', 'block', 'is_owner', 'move_in_date')
    list_filter = ('is_owner', 'block', 'move_in_date')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'apartment_number')
    inlines = [ResidentContactInline]

@admin.register(ResidentContact)
class ResidentContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'resident', 'phone_number', 'relationship', 'is_emergency_contact')
    list_filter = ('is_emergency_contact', 'relationship')
    search_fields = ('name', 'phone_number', 'resident__user__email')