"""
Packing serializers for Order Fulfillment & Distribution.
"""

from rest_framework import serializers
from decimal import Decimal

from ..models import PackingTask, Package, PackageItem


class PackageItemSerializer(serializers.ModelSerializer):
    """Serializer for PackageItem model."""

    product_sku = serializers.CharField(source='order_item.product_sku', read_only=True)
    product_name = serializers.CharField(source='order_item.product_name', read_only=True)

    class Meta:
        model = PackageItem
        fields = [
            'id', 'order_item', 'product_sku', 'product_name', 'quantity',
            'position_x', 'position_y', 'position_z'
        ]
        read_only_fields = ['id']


class PackageSerializer(serializers.ModelSerializer):
    """Serializer for Package model."""

    volume = serializers.SerializerMethodField()
    net_weight = serializers.SerializerMethodField()
    is_overweight = serializers.SerializerMethodField()

    items = PackageItemSerializer(many=True, read_only=True)

    class Meta:
        model = Package
        fields = [
            'id', 'package_number', 'package_type', 'length', 'width', 'height',
            'volume', 'empty_weight', 'gross_weight', 'net_weight', 'max_weight',
            'is_overweight', 'is_sealed', 'notes', 'metadata', 'created_at',
            'sealed_at', 'items'
        ]
        read_only_fields = ['id', 'package_number', 'created_at', 'sealed_at']

    def get_volume(self, obj):
        return obj.volume

    def get_net_weight(self, obj):
        return obj.net_weight

    def get_is_overweight(self, obj):
        return obj.is_overweight

    def validate_gross_weight(self, value):
        """Validate gross weight."""
        if value is not None and value < 0:
            raise serializers.ValidationError("Gross weight cannot be negative")
        return value

    def validate_max_weight(self, value):
        """Validate max weight."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Max weight must be greater than 0")
        return value

    def validate(self, data):
        """Validate package dimensions and weight."""
        length = data.get('length')
        width = data.get('width')
        height = data.get('height')
        max_weight = data.get('max_weight')
        empty_weight = data.get('empty_weight', Decimal('0.00'))

        # Validate dimensions
        if all([length, width, height]):
            if any(dim <= 0 for dim in [length, width, height]):
                raise serializers.ValidationError("Package dimensions must be greater than 0")

        # Validate weight relationship
        if max_weight and empty_weight >= max_weight:
            raise serializers.ValidationError("Empty weight cannot be greater than or equal to max weight")

        return data


class PackingTaskListSerializer(serializers.ModelSerializer):
    """Serializer for packing task listing."""

    order_number = serializers.CharField(source='order.order_number', read_only=True)
    packer_name = serializers.CharField(source='packer.username', read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = PackingTask
        fields = [
            'id', 'task_number', 'order_number', 'packer_name', 'status',
            'progress_percentage', 'total_items', 'completed_items',
            'assigned_at', 'created_at'
        ]

    def get_progress_percentage(self, obj):
        return obj.progress_percentage


class PackingTaskDetailSerializer(serializers.ModelSerializer):
    """Serializer for packing task details."""

    order_number = serializers.CharField(source='order.order_number', read_only=True)
    packer_name = serializers.CharField(source='packer.username', read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    packages = PackageSerializer(many=True, read_only=True)

    class Meta:
        model = PackingTask
        fields = [
            'id', 'task_number', 'order_number', 'packer_name', 'status',
            'progress_percentage', 'total_items', 'completed_items',
            'notes', 'assigned_at', 'started_at', 'completed_at',
            'created_at', 'updated_at', 'packages'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_progress_percentage(self, obj):
        return obj.progress_percentage


class PackageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating packages."""

    class Meta:
        model = Package
        fields = [
            'package_type', 'length', 'width', 'height', 'empty_weight',
            'max_weight', 'notes', 'metadata'
        ]

    def validate(self, data):
        """Validate package creation data."""
        # Ensure required fields for validation
        return super().validate(data)


class PackageItemAddSerializer(serializers.Serializer):
    """Serializer for adding items to packages."""

    order_item_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=4)
    position_x = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    position_y = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    position_z = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)

    def validate_quantity(self, value):
        """Validate quantity."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value

    def validate(self, data):
        """Validate item addition."""
        # Check if positions are provided consistently
        positions = ['position_x', 'position_y', 'position_z']
        provided_positions = [pos for pos in positions if pos in data]

        if provided_positions and len(provided_positions) != 3:
            raise serializers.ValidationError("All three position coordinates must be provided together")

        return data


class PackingTaskSummarySerializer(serializers.ModelSerializer):
    """Serializer for packing task summary."""

    order_number = serializers.CharField(source='order.order_number', read_only=True)
    packer_name = serializers.CharField(source='packer.username', read_only=True)

    packages_summary = serializers.SerializerMethodField()

    class Meta:
        model = PackingTask
        fields = [
            'id', 'task_number', 'order_number', 'packer_name', 'status',
            'progress_percentage', 'total_items', 'completed_items',
            'packages_summary', 'assigned_at', 'started_at', 'completed_at'
        ]

    def get_packages_summary(self, obj):
        """Get summary of packages in task."""
        packages = obj.packages.all()
        return {
            'total_packages': packages.count(),
            'sealed_packages': packages.filter(is_sealed=True).count(),
            'total_weight': sum((pkg.gross_weight or 0) for pkg in packages),
            'total_volume': sum((pkg.volume or 0) for pkg in packages),
        }
