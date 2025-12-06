"""
Shipment serializers for Order Fulfillment & Distribution.
"""

from rest_framework import serializers

from ..models import Shipment, ShipmentItem, ShipmentStatus


class ShipmentItemSerializer(serializers.ModelSerializer):
    """Serializer for ShipmentItem model."""

    package_number = serializers.CharField(source='package.package_number', read_only=True)
    package_type = serializers.CharField(source='package.package_type', read_only=True)
    package_weight = serializers.DecimalField(source='package.gross_weight', max_digits=8, decimal_places=2, read_only=True)

    class Meta:
        model = ShipmentItem
        fields = [
            'id', 'package', 'package_number', 'package_type', 'package_weight',
            'sequence_number'
        ]
        read_only_fields = ['id']


class ShipmentListSerializer(serializers.ModelSerializer):
    """Serializer for shipment listing."""

    order_number = serializers.CharField(source='order.order_number', read_only=True)
    package_count = serializers.SerializerMethodField()
    has_tracking = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = [
            'id', 'shipment_number', 'order_number', 'carrier', 'status',
            'tracking_number', 'has_tracking', 'package_count', 'total_weight',
            'shipping_cost', 'estimated_delivery_date', 'created_at'
        ]

    def get_package_count(self, obj):
        return obj.shipment_items.count()

    def get_has_tracking(self, obj):
        return bool(obj.tracking_number)


class ShipmentDetailSerializer(serializers.ModelSerializer):
    """Serializer for shipment details."""

    order_number = serializers.CharField(source='order.order_number', read_only=True)
    dispatcher_name = serializers.CharField(source='dispatcher.username', read_only=True)

    shipment_items = ShipmentItemSerializer(many=True, read_only=True)

    # Delivery info
    delivery_delay_days = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = [
            'id', 'shipment_number', 'order_number', 'carrier', 'tracking_number',
            'status', 'shipping_cost', 'insurance_cost', 'total_weight',
            'total_volume', 'ship_from_address', 'ship_to_address', 'manifest',
            'dispatcher_name', 'estimated_delivery_date', 'actual_delivery_date',
            'delivered_by', 'recipient_name', 'notes', 'metadata',
            'dispatched_at', 'delivered_at', 'created_at', 'updated_at',
            'shipment_items', 'delivery_delay_days'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_delivery_delay_days(self, obj):
        return obj.delivery_delay_days


class ShipmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating shipments."""

    class Meta:
        model = Shipment
        fields = [
            'carrier', 'shipping_cost', 'insurance_cost', 'ship_from_address',
            'ship_to_address', 'estimated_delivery_date', 'notes', 'metadata'
        ]

    def validate_carrier(self, value):
        """Validate carrier."""
        if not value or not value.strip():
            raise serializers.ValidationError("Carrier must be specified")
        return value.strip()

    def validate_shipping_cost(self, value):
        """Validate shipping cost."""
        if value < 0:
            raise serializers.ValidationError("Shipping cost cannot be negative")
        return value

    def validate_insurance_cost(self, value):
        """Validate insurance cost."""
        if value < 0:
            raise serializers.ValidationError("Insurance cost cannot be negative")
        return value

    def validate_ship_from_address(self, value):
        """Validate ship from address."""
        required_fields = ['street', 'city', 'country']
        if not all(field in value for field in required_fields):
            raise serializers.ValidationError("Ship from address must include street, city, and country")
        return value

    def validate_ship_to_address(self, value):
        """Validate ship to address."""
        required_fields = ['street', 'city', 'country']
        if not all(field in value for field in required_fields):
            raise serializers.ValidationError("Ship to address must include street, city, and country")
        return value


class ShipmentTrackingSerializer(serializers.Serializer):
    """Serializer for assigning tracking numbers."""

    tracking_number = serializers.CharField(max_length=100)

    def validate_tracking_number(self, value):
        """Validate tracking number."""
        if not value or not value.strip():
            raise serializers.ValidationError("Tracking number cannot be empty")
        return value.strip()


class ShipmentStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating shipment status."""

    status = serializers.ChoiceField(choices=ShipmentStatus.choices)
    tracking_number = serializers.CharField(max_length=100, required=False)
    recipient_name = serializers.CharField(max_length=100, required=False)
    delivered_by = serializers.CharField(max_length=100, required=False)
    notes = serializers.CharField(required=False)

    def validate(self, data):
        """Validate status-specific requirements."""
        status = data.get('status')

        # Validate required fields for DELIVERED status
        if status == ShipmentStatus.DELIVERED:
            if not data.get('recipient_name'):
                raise serializers.ValidationError("Recipient name is required for delivery")

        return data


class ShipmentManifestSerializer(serializers.Serializer):
    """Serializer for shipment manifest."""

    shipment_number = serializers.CharField(read_only=True)
    order_number = serializers.CharField(read_only=True)
    carrier = serializers.CharField(read_only=True)
    tracking_number = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    ship_from = serializers.DictField(read_only=True)
    ship_to = serializers.DictField(read_only=True)
    total_weight = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    total_volume = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    estimated_delivery = serializers.DateTimeField(read_only=True)
    packages = serializers.ListField(read_only=True)


class ShipmentSummarySerializer(serializers.ModelSerializer):
    """Serializer for shipment summary."""

    order_number = serializers.CharField(source='order.order_number', read_only=True)

    package_count = serializers.SerializerMethodField()
    is_delivered = serializers.SerializerMethodField()
    is_in_transit = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = [
            'id', 'shipment_number', 'order_number', 'carrier', 'status',
            'tracking_number', 'package_count', 'total_weight', 'shipping_cost',
            'estimated_delivery_date', 'actual_delivery_date', 'is_delivered',
            'is_in_transit', 'dispatched_at', 'delivered_at'
        ]

    def get_package_count(self, obj):
        return obj.shipment_items.count()

    def get_is_delivered(self, obj):
        return obj.is_delivered

    def get_is_in_transit(self, obj):
        return obj.is_in_transit
