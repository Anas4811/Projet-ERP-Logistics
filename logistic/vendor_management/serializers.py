from rest_framework import serializers
from .models import Vendor, VendorContact, PurchaseOrder, PurchaseOrderItem, Notification


class VendorContactSerializer(serializers.ModelSerializer):
    """Serializer for vendor contacts."""
    class Meta:
        model = VendorContact
        fields = [
            'id', 'name', 'position', 'email', 'phone', 'is_primary',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class VendorSerializer(serializers.ModelSerializer):
    """Serializer for vendors."""
    contacts = VendorContactSerializer(many=True, read_only=True)
    contact_count = serializers.IntegerField(read_only=True)
    active_pos = serializers.IntegerField(read_only=True)
    recent_pos = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            'id', 'name', 'vendor_code', 'contact_person', 'email', 'phone',
            'address', 'city', 'state', 'country', 'postal_code',
            'tax_id', 'registration_number', 'payment_terms',
            'rating', 'on_time_delivery_rate', 'quality_rating',
            'status', 'is_preferred', 'created_by', 'created_at', 'updated_at',
            'contacts', 'contact_count', 'active_pos', 'recent_pos'
        ]
        read_only_fields = ['created_at', 'updated_at', 'vendor_code']

    def get_recent_pos(self, obj):
        """Get recent purchase orders for this vendor."""
        from .models import PurchaseOrder
        recent_pos = PurchaseOrder.objects.filter(vendor=obj).order_by('-created_at')[:5]
        return PurchaseOrderListSerializer(recent_pos, many=True).data


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for purchase order items."""
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    quantity_pending = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_fully_received = serializers.BooleanField(read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'purchase_order', 'item_code', 'item_description',
            'quantity_ordered', 'quantity_received', 'unit_price', 'line_total',
            'expected_delivery_date', 'notes', 'quantity_pending', 'is_fully_received'
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Serializer for purchase orders."""
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'vendor', 'vendor_name', 'order_date',
            'expected_delivery_date', 'actual_delivery_date', 'subtotal',
            'tax_amount', 'discount_amount', 'total_amount', 'status',
            'priority', 'approved_by', 'approved_by_name', 'approved_at',
            'approval_notes', 'shipping_address', 'special_instructions',
            'internal_notes', 'created_by', 'created_by_name', 'created_at',
            'updated_at', 'is_overdue', 'items', 'item_count'
        ]
        read_only_fields = ['po_number', 'created_at', 'updated_at', 'approved_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class PurchaseOrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating purchase orders."""
    items = PurchaseOrderItemSerializer(many=True, required=False)

    class Meta:
        model = PurchaseOrder
        fields = [
            'vendor', 'order_date', 'expected_delivery_date', 'priority',
            'shipping_address', 'special_instructions', 'internal_notes', 'items'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        validated_data['created_by'] = self.context['request'].user
        po = super().create(validated_data)

        # Create PO items
        for item_data in items_data:
            PurchaseOrderItem.objects.create(purchase_order=po, **item_data)

        return po


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for PO lists."""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'vendor_name', 'status', 'priority',
            'order_date', 'expected_delivery_date', 'total_amount',
            'is_overdue', 'created_by_name', 'created_at'
        ]


class PurchaseOrderApprovalSerializer(serializers.Serializer):
    """Serializer for PO approval/rejection."""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        po = self.context['po']
        if data['action'] == 'approve' and po.status != 'PENDING_APPROVAL':
            raise serializers.ValidationError("PO is not pending approval.")
        return data


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""
    recipient_email = serializers.CharField(source='recipient.email', read_only=True)
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    po_number = serializers.CharField(source='related_po.po_number', read_only=True)
    vendor_name = serializers.CharField(source='related_vendor.name', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_email', 'recipient_name',
            'notification_type', 'priority', 'title', 'message',
            'related_po', 'po_number', 'related_vendor', 'vendor_name',
            'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['created_at', 'read_at']


class VendorPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for vendor performance reports."""
    total_pos = serializers.IntegerField(read_only=True)
    on_time_deliveries = serializers.IntegerField(read_only=True)
    avg_rating = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)
    on_time_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            'id', 'name', 'vendor_code', 'status', 'is_preferred',
            'rating', 'on_time_delivery_rate', 'quality_rating',
            'total_pos', 'on_time_deliveries', 'avg_rating', 'on_time_percentage'
        ]

    def get_on_time_percentage(self, obj):
        if obj.total_pos and obj.total_pos > 0:
            return round((obj.on_time_deliveries / obj.total_pos) * 100, 2)
        return 0.00


class POStatusReportSerializer(serializers.Serializer):
    """Serializer for PO status reports."""
    status = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.SerializerMethodField()

    def get_percentage(self, obj):
        total = sum(item['count'] for item in self.context.get('all_statuses', []))
        if total > 0:
            return round((obj['count'] / total) * 100, 2)
        return 0.00
