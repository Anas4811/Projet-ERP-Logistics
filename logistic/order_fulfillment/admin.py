"""
Django admin configuration for Order Fulfillment & Distribution.
"""

from django.contrib import admin
from .models import (
    Order, OrderItem, Allocation, PickingTask, PickingItem,
    PackingTask, Package, PackageItem, Shipment, ShipmentItem, AuditLog
)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'status', 'priority', 'total_amount', 'created_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['order_number', 'customer__username']
    readonly_fields = ['id', 'order_number', 'created_at', 'updated_at']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_sku', 'quantity_ordered', 'quantity_allocated', 'quantity_picked']
    list_filter = ['order__status']
    search_fields = ['product_sku', 'order__order_number']
    readonly_fields = ['id']


@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    list_display = ['order', 'order_item', 'location', 'quantity_reserved', 'status', 'allocated_at']
    list_filter = ['status', 'allocated_at']
    search_fields = ['order__order_number', 'reservation_id']
    readonly_fields = ['id', 'allocated_at']


@admin.register(PickingTask)
class PickingTaskAdmin(admin.ModelAdmin):
    list_display = ['task_number', 'order', 'picker', 'status', 'progress_percentage', 'created_at']
    list_filter = ['status', 'zone', 'created_at']
    search_fields = ['task_number', 'order__order_number', 'picker__username']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(PickingItem)
class PickingItemAdmin(admin.ModelAdmin):
    list_display = ['picking_task', 'order_item', 'quantity_to_pick', 'quantity_picked', 'is_completed']
    list_filter = ['is_completed']
    search_fields = ['picking_task__task_number', 'order_item__product_sku']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(PackingTask)
class PackingTaskAdmin(admin.ModelAdmin):
    list_display = ['task_number', 'order', 'packer', 'status', 'progress_percentage', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['task_number', 'order__order_number', 'packer__username']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['package_number', 'packing_task', 'package_type', 'gross_weight', 'is_sealed']
    list_filter = ['package_type', 'is_sealed']
    search_fields = ['package_number', 'packing_task__task_number']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(PackageItem)
class PackageItemAdmin(admin.ModelAdmin):
    list_display = ['package', 'order_item', 'quantity']
    search_fields = ['package__package_number', 'order_item__product_sku']
    readonly_fields = ['id']


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ['shipment_number', 'order', 'carrier', 'status', 'tracking_number', 'created_at']
    list_filter = ['status', 'carrier', 'created_at']
    search_fields = ['shipment_number', 'order__order_number', 'tracking_number']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ShipmentItem)
class ShipmentItemAdmin(admin.ModelAdmin):
    list_display = ['shipment', 'package', 'sequence_number']
    search_fields = ['shipment__shipment_number', 'package__package_number']
    readonly_fields = ['id']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['entity_type', 'entity_id', 'action', 'user', 'timestamp']
    list_filter = ['entity_type', 'action', 'timestamp']
    search_fields = ['entity_type', 'entity_id', 'user__username']
    readonly_fields = ['id', 'timestamp']
