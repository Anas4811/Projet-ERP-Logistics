from django.contrib import admin
from .models import Vendor, VendorContact, PurchaseOrder, PurchaseOrderItem, Notification


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'vendor_code', 'email', 'phone', 'status', 'is_preferred', 'rating']
    list_filter = ['status', 'is_preferred', 'country']
    search_fields = ['name', 'vendor_code', 'email']
    ordering = ['name']


@admin.register(VendorContact)
class VendorContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'vendor', 'email', 'phone', 'is_primary']
    list_filter = ['is_primary', 'vendor']
    search_fields = ['name', 'email', 'vendor__name']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'vendor', 'status', 'priority', 'order_date', 'total_amount', 'is_overdue']
    list_filter = ['status', 'priority', 'order_date', 'vendor']
    search_fields = ['po_number', 'vendor__name']
    ordering = ['-created_at']
    readonly_fields = ['po_number']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vendor', 'created_by', 'approved_by')


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ['purchase_order', 'item_code', 'item_description', 'quantity_ordered', 'quantity_received', 'unit_price']
    list_filter = ['purchase_order__status']
    search_fields = ['item_code', 'item_description', 'purchase_order__po_number']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'recipient__email']
    ordering = ['-created_at']
