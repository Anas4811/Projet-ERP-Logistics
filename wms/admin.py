from django.contrib import admin

from .models import (
    Aisle,
    Bin,
    OutboundOrder,
    OutboundOrderLine,
    PickConfirmation,
    Product,
    PutawayRule,
    Rack,
    StockItem,
    StockMovement,
    Warehouse,
    Zone,
)

# Register your models here.


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'capacity')
    search_fields = ('name', 'location')


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'warehouse')
    list_filter = ('warehouse',)
    search_fields = ('name', 'warehouse__name')


@admin.register(Aisle)
class AisleAdmin(admin.ModelAdmin):
    list_display = ('name', 'zone')
    list_filter = ('zone__warehouse', 'zone')
    search_fields = ('name', 'zone__name', 'zone__warehouse__name')


@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_display = ('name', 'aisle')
    list_filter = ('aisle__zone__warehouse', 'aisle__zone', 'aisle')
    search_fields = ('name', 'aisle__name', 'aisle__zone__name')


@admin.register(Bin)
class BinAdmin(admin.ModelAdmin):
    list_display = ('name', 'rack', 'capacity')
    list_filter = ('rack__aisle__zone__warehouse', 'rack__aisle__zone', 'rack__aisle', 'rack')
    search_fields = ('name', 'rack__name', 'rack__aisle__name')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'unit', 'default_expiry_date')
    search_fields = ('sku', 'name', 'category')
    list_filter = ('category', 'unit')


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'bin', 'quantity', 'batch_number', 'serial_number', 'expiry_date', 'updated_at')
    list_filter = ('product__category', 'expiry_date', 'bin__rack__aisle__zone__warehouse')
    search_fields = ('product__sku', 'product__name', 'bin__name', 'batch_number', 'serial_number')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('movement_type', 'product', 'quantity', 'from_bin', 'to_bin', 'reference', 'created_at')
    list_filter = ('movement_type', 'created_at')
    search_fields = ('reference', 'product__sku', 'product__name')


@admin.register(PutawayRule)
class PutawayRuleAdmin(admin.ModelAdmin):
    list_display = ('priority', 'product', 'product_category', 'zone')
    list_filter = ('zone__warehouse', 'zone')
    search_fields = ('product__sku', 'product_category', 'zone__name')


class OutboundOrderLineInline(admin.TabularInline):
    model = OutboundOrderLine
    extra = 0


@admin.register(OutboundOrder)
class OutboundOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number',)
    inlines = [OutboundOrderLineInline]


@admin.register(OutboundOrderLine)
class OutboundOrderLineAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity_requested', 'quantity_picked')
    list_filter = ('order__status',)
    search_fields = ('order__order_number', 'product__sku', 'product__name')


@admin.register(PickConfirmation)
class PickConfirmationAdmin(admin.ModelAdmin):
    list_display = ('order_line', 'from_bin', 'quantity', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('order_line__order__order_number', 'order_line__product__sku')
