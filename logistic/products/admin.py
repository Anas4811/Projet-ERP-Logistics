from django.contrib import admin
from .models import Product, ProductCategory


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    search_fields = ["name", "description"]
    list_filter = ["created_at"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "category", "unit", "is_active", "created_at"]
    list_filter = ["category", "unit", "is_active", "created_at"]
    search_fields = ["name", "sku", "description"]
    readonly_fields = ["created_at", "updated_at"]

