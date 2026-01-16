from django.contrib import admin
from .models import ASN, ASNItem, ShipmentSchedule, InboundTracking


@admin.register(ASN)
class ASNAdmin(admin.ModelAdmin):
    list_display = ['asn_number', 'purchase_order', 'vendor', 'status', 'expected_arrival_date', 'actual_arrival_date', 'is_overdue']
    list_filter = ['status', 'expected_arrival_date', 'actual_arrival_date', 'vendor']
    search_fields = ['asn_number', 'purchase_order__po_number', 'vendor__name']
    ordering = ['-created_at']
    readonly_fields = ['asn_number']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('purchase_order', 'vendor', 'created_by', 'approved_by')


@admin.register(ASNItem)
class ASNItemAdmin(admin.ModelAdmin):
    list_display = ['asn', 'item_code', 'item_description', 'quantity_expected', 'quantity_received', 'has_damage']
    list_filter = ['has_damage', 'asn__status']
    search_fields = ['item_code', 'item_description', 'asn__asn_number']


@admin.register(ShipmentSchedule)
class ShipmentScheduleAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'frequency', 'day_of_week', 'day_of_month', 'is_active']
    list_filter = ['frequency', 'is_active', 'day_of_week']
    search_fields = ['vendor__name', 'default_carrier']


@admin.register(InboundTracking)
class InboundTrackingAdmin(admin.ModelAdmin):
    list_display = ['asn', 'current_location', 'estimated_arrival', 'last_contact', 'updated_at']
    list_filter = ['last_contact', 'updated_at']
    search_fields = ['asn__asn_number', 'current_location', 'contact_person']
    ordering = ['-updated_at']
