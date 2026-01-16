from rest_framework import serializers
from .models import ASN, ASNItem, ShipmentSchedule, InboundTracking


class ASNItemSerializer(serializers.ModelSerializer):
    """Serializer for ASN items."""
    po_item_description = serializers.CharField(source='purchase_order_item.item_description', read_only=True)
    quantity_pending = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_fully_received = serializers.BooleanField(read_only=True)

    class Meta:
        model = ASNItem
        fields = [
            'id', 'asn', 'purchase_order_item', 'po_item_description',
            'quantity_expected', 'quantity_received', 'item_code', 'item_description',
            'unit_price', 'condition', 'quality_notes', 'has_damage', 'damage_description',
            'batch_number', 'serial_numbers', 'expiry_date', 'received_by',
            'received_at', 'quantity_pending', 'is_fully_received'
        ]
        read_only_fields = ['received_at']


class ASNSerializer(serializers.ModelSerializer):
    """Serializer for ASNs."""
    items = ASNItemSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_quantity = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ASN
        fields = [
            'id', 'asn_number', 'purchase_order', 'po_number', 'vendor', 'vendor_name',
            'carrier_name', 'tracking_number', 'vehicle_number', 'driver_name',
            'driver_phone', 'expected_ship_date', 'actual_ship_date',
            'expected_arrival_date', 'actual_arrival_date', 'status',
            'approved_by', 'approved_by_name', 'approved_at', 'notes',
            'special_instructions', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'is_overdue', 'items',
            'total_items', 'total_quantity'
        ]
        read_only_fields = ['asn_number', 'created_at', 'updated_at', 'approved_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ASNCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ASNs from POs."""
    items = ASNItemSerializer(many=True, required=False)

    class Meta:
        model = ASN
        fields = [
            'purchase_order', 'expected_ship_date', 'expected_arrival_date',
            'carrier_name', 'tracking_number', 'vehicle_number', 'driver_name',
            'driver_phone', 'notes', 'special_instructions', 'items'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        validated_data['created_by'] = self.context['request'].user

        # Get vendor from PO
        po = validated_data['purchase_order']
        validated_data['vendor'] = po.vendor

        asn = super().create(validated_data)

        # Create ASN items if provided, otherwise auto-create from PO
        if items_data:
            for item_data in items_data:
                ASNItem.objects.create(asn=asn, **item_data)
        else:
            # Auto-create from PO items
            for po_item in po.items.all():
                ASNItem.objects.create(
                    asn=asn,
                    purchase_order_item=po_item,
                    item_code=po_item.item_code,
                    item_description=po_item.item_description,
                    quantity_expected=po_item.quantity_ordered - po_item.quantity_received,
                    unit_price=po_item.unit_price,
                )

        return asn


class ASNListSerializer(serializers.ModelSerializer):
    """Simplified serializer for ASN lists."""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    total_quantity = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ASN
        fields = [
            'id', 'asn_number', 'po_number', 'vendor_name', 'status',
            'expected_arrival_date', 'actual_arrival_date', 'carrier_name',
            'tracking_number', 'is_overdue', 'total_quantity', 'created_at'
        ]


class ASNStatusUpdateSerializer(serializers.Serializer):
    """Serializer for ASN status updates."""
    status = serializers.ChoiceField(choices=[
        ('CREATED', 'Created'),
        ('APPROVED', 'Approved'),
        ('IN_TRANSIT', 'In Transit'),
        ('ARRIVED', 'Arrived'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected'),
    ])
    actual_ship_date = serializers.DateField(required=False)
    actual_arrival_date = serializers.DateField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class ShipmentScheduleSerializer(serializers.ModelSerializer):
    """Serializer for shipment schedules."""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)

    class Meta:
        model = ShipmentSchedule
        fields = [
            'id', 'vendor', 'vendor_name', 'frequency', 'day_of_week',
            'day_of_month', 'preferred_time_start', 'preferred_time_end',
            'default_carrier', 'default_driver', 'is_active', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class InboundTrackingSerializer(serializers.ModelSerializer):
    """Serializer for inbound tracking."""
    asn_number = serializers.CharField(source='asn.asn_number', read_only=True)
    vendor_name = serializers.CharField(source='asn.vendor.name', read_only=True)

    class Meta:
        model = InboundTracking
        fields = [
            'id', 'asn', 'asn_number', 'vendor_name', 'current_location',
            'latitude', 'longitude', 'last_status_update', 'status_notes',
            'estimated_arrival', 'delay_reason', 'last_contact',
            'contact_person', 'updated_at'
        ]
        read_only_fields = ['updated_at']


class ExpectedArrivalsSerializer(serializers.ModelSerializer):
    """Serializer for expected arrivals report."""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    days_until_arrival = serializers.SerializerMethodField()

    class Meta:
        model = ASN
        fields = [
            'id', 'asn_number', 'po_number', 'vendor_name', 'expected_arrival_date',
            'carrier_name', 'tracking_number', 'status', 'days_until_arrival'
        ]

    def get_days_until_arrival(self, obj):
        from django.utils import timezone
        if obj.expected_arrival_date:
            delta = obj.expected_arrival_date - timezone.now().date()
            return delta.days
        return None


class DeliveryPerformanceSerializer(serializers.Serializer):
    """Serializer for delivery performance reports."""
    asn_number = serializers.CharField()
    vendor_name = serializers.CharField()
    expected_date = serializers.DateField()
    actual_date = serializers.DateField()
    days_variance = serializers.IntegerField()
    status = serializers.CharField()
    on_time = serializers.BooleanField()
