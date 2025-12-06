from rest_framework import serializers
from .models import StorageLocation, PutawayRule, StockItem, StockMovement
from products.serializers import ProductSerializer, ProductCategorySerializer


class StorageLocationSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    parent_code = serializers.CharField(source="parent.code", read_only=True)
    full_path = serializers.CharField(read_only=True)
    allowed_categories_detail = ProductCategorySerializer(source="allowed_categories", many=True, read_only=True)

    class Meta:
        model = StorageLocation
        fields = [
            "id",
            "code",
            "name",
            "level",
            "parent",
            "parent_name",
            "parent_code",
            "storage_type",
            "capacity",
            "capacity_unit",
            "allowed_categories",
            "allowed_categories_detail",
            "is_active",
            "notes",
            "full_path",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PutawayRuleSerializer(serializers.ModelSerializer):
    product_category_name = serializers.CharField(source="product_category.name", read_only=True)

    class Meta:
        model = PutawayRule
        fields = [
            "id",
            "name",
            "description",
            "product_category",
            "product_category_name",
            "storage_type",
            "priority",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StockItemSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source="product", read_only=True)
    location_code = serializers.CharField(source="location.code", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    available_quantity = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = StockItem
        fields = [
            "id",
            "location",
            "location_code",
            "location_name",
            "product",
            "product_detail",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "last_movement_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "last_movement_date"]


class StockMovementSerializer(serializers.ModelSerializer):
    product_detail = ProductSerializer(source="product", read_only=True)
    from_location_code = serializers.CharField(source="from_location.code", read_only=True)
    to_location_code = serializers.CharField(source="to_location.code", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "movement_type",
            "from_location",
            "from_location_code",
            "to_location",
            "to_location_code",
            "product",
            "product_detail",
            "quantity",
            "user",
            "user_name",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class StockMovementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ["movement_type", "from_location", "to_location", "product", "quantity", "notes"]

