from django.contrib import admin
from .models import StorageLocation, PutawayRule, StockItem, StockMovement


@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "level", "parent", "storage_type", "capacity", "is_active", "created_at"]
    list_filter = ["level", "storage_type", "is_active", "created_at"]
    search_fields = ["code", "name", "notes"]
    filter_horizontal = ["allowed_categories"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(PutawayRule)
class PutawayRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "product_category", "storage_type", "priority", "is_active", "created_at"]
    list_filter = ["product_category", "storage_type", "priority", "is_active", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ["product", "location", "quantity", "reserved_quantity", "last_movement_date"]
    list_filter = ["location", "product__category", "last_movement_date"]
    search_fields = ["product__name", "product__sku", "location__code"]
    readonly_fields = ["created_at", "updated_at", "last_movement_date"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["movement_type", "product", "from_location", "to_location", "quantity", "user", "created_at"]
    list_filter = ["movement_type", "created_at", "user"]
    search_fields = ["product__name", "product__sku", "notes"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"

