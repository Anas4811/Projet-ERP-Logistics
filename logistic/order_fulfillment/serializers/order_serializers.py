"""
Order serializers for Order Fulfillment & Distribution.
"""

from rest_framework import serializers
from decimal import Decimal

from ..models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model."""

    # Read-only computed fields
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_weight = serializers.DecimalField(max_digits=12, decimal_places=4, read_only=True)

    # Additional computed fields
    remaining_to_allocate = serializers.SerializerMethodField()
    remaining_to_pick = serializers.SerializerMethodField()
    remaining_to_pack = serializers.SerializerMethodField()
    remaining_to_ship = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_id', 'product_sku', 'product_name',
            'quantity_ordered', 'quantity_allocated', 'quantity_picked',
            'quantity_packed', 'quantity_shipped', 'unit_price',
            'unit_weight', 'line_total', 'total_weight',
            'remaining_to_allocate', 'remaining_to_pick',
            'remaining_to_pack', 'remaining_to_ship',
            'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_remaining_to_allocate(self, obj):
        return obj.remaining_to_allocate

    def get_remaining_to_pick(self, obj):
        return obj.remaining_to_pick

    def get_remaining_to_pack(self, obj):
        return obj.remaining_to_pack

    def get_remaining_to_ship(self, obj):
        return obj.remaining_to_ship

    def validate_quantity_ordered(self, value):
        """Validate ordered quantity."""
        if value <= 0:
            raise serializers.ValidationError("Quantity ordered must be greater than 0")
        return value

    def validate_unit_price(self, value):
        """Validate unit price."""
        if value < 0:
            raise serializers.ValidationError("Unit price cannot be negative")
        return value

    def validate_unit_weight(self, value):
        """Validate unit weight."""
        if value is not None and value < 0:
            raise serializers.ValidationError("Unit weight cannot be negative")
        return value


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders."""

    items = OrderItemSerializer(many=True, write_only=True)
    customer = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Order
        fields = [
            'customer', 'warehouse_id', 'priority', 'notes',
            'metadata', 'items'
        ]

    def validate_items(self, value):
        """Validate order items."""
        if not value:
            raise serializers.ValidationError("Order must contain at least one item")

        # Check for duplicate products
        skus = [item['product_sku'] for item in value]
        if len(skus) != len(set(skus)):
            raise serializers.ValidationError("Duplicate products in order")

        return value

    def validate_warehouse_id(self, value):
        """Validate warehouse ID."""
        if not value:
            raise serializers.ValidationError("Warehouse must be specified")
        return value

    def create(self, validated_data):
        """Create order with items."""
        from ..services import OrderService

        items_data = validated_data.pop('items')
        order_data = validated_data
        order_data['items'] = items_data

        return OrderService.create_order(
            customer=validated_data['customer'],
            order_data=order_data,
            created_by=self.context['request'].user
        )


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating orders."""

    class Meta:
        model = Order
        fields = ['priority', 'notes', 'metadata', 'tax_amount', 'shipping_amount']

    def validate_tax_amount(self, value):
        """Validate tax amount."""
        if value < 0:
            raise serializers.ValidationError("Tax amount cannot be negative")
        return value

    def validate_shipping_amount(self, value):
        """Validate shipping amount."""
        if value < 0:
            raise serializers.ValidationError("Shipping amount cannot be negative")
        return value


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for order listing."""

    customer_name = serializers.CharField(source='customer.username', read_only=True)
    items_count = serializers.SerializerMethodField()
    allocated_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'status', 'priority',
            'total_amount', 'items_count', 'allocated_percentage',
            'created_at', 'updated_at'
        ]

    def get_items_count(self, obj):
        return obj.items.count()

    def get_allocated_percentage(self, obj):
        """Calculate allocation percentage."""
        items = obj.items.all()
        if not items:
            return 0

        total_ordered = sum(item.quantity_ordered for item in items)
        total_allocated = sum(item.quantity_allocated for item in items)

        if total_ordered == 0:
            return 0

        return round((total_allocated / total_ordered) * 100, 2)


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order details."""

    customer_name = serializers.CharField(source='customer.username', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.username', read_only=True)

    items = OrderItemSerializer(many=True, read_only=True)

    # Computed totals
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_weight = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'status', 'priority',
            'subtotal', 'tax_amount', 'shipping_amount', 'total_amount',
            'total_weight', 'warehouse_id', 'notes', 'metadata',
            'created_by_name', 'updated_by_name', 'created_at', 'updated_at',
            'items'
        ]

    def get_total_weight(self, obj):
        """Calculate total order weight."""
        return sum((item.total_weight or 0) for item in obj.items.all())


class OrderSummarySerializer(serializers.ModelSerializer):
    """Serializer for order summary."""

    customer_name = serializers.CharField(source='customer.username', read_only=True)
    items_count = serializers.SerializerMethodField()
    picking_tasks_count = serializers.SerializerMethodField()
    packing_tasks_count = serializers.SerializerMethodField()
    shipments_count = serializers.SerializerMethodField()

    progress = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'status', 'priority',
            'total_amount', 'items_count', 'picking_tasks_count',
            'packing_tasks_count', 'shipments_count', 'progress',
            'created_at'
        ]

    def get_items_count(self, obj):
        return obj.items.count()

    def get_picking_tasks_count(self, obj):
        return obj.picking_tasks.count()

    def get_packing_tasks_count(self, obj):
        return obj.packing_tasks.count()

    def get_shipments_count(self, obj):
        return obj.shipments.count()

    def get_progress(self, obj):
        """Calculate order fulfillment progress."""
        status_progress = {
            'CREATED': 10,
            'APPROVED': 20,
            'ALLOCATED': 40,
            'PICKING': 60,
            'PACKING': 80,
            'SHIPPED': 90,
            'DELIVERED': 100,
            'CANCELLED': 0,
        }
        return status_progress.get(obj.status, 0)
