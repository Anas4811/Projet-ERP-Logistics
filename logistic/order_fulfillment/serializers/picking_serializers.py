"""
Picking serializers for Order Fulfillment & Distribution.
"""

from rest_framework import serializers

from ..models import PickingTask, PickingItem


class PickingItemSerializer(serializers.ModelSerializer):
    """Serializer for PickingItem model."""

    product_sku = serializers.CharField(source='order_item.product_sku', read_only=True)
    product_name = serializers.CharField(source='order_item.product_name', read_only=True)
    remaining_to_pick = serializers.SerializerMethodField()

    class Meta:
        model = PickingItem
        fields = [
            'id', 'order_item', 'product_sku', 'product_name',
            'quantity_to_pick', 'quantity_picked', 'remaining_to_pick',
            'location', 'is_completed', 'picked_at', 'created_at'
        ]
        read_only_fields = ['id', 'picked_at', 'created_at']

    def get_remaining_to_pick(self, obj):
        return obj.remaining_to_pick


class PickingTaskListSerializer(serializers.ModelSerializer):
    """Serializer for picking task listing."""

    order_number = serializers.CharField(source='order.order_number', read_only=True)
    picker_name = serializers.CharField(source='picker.username', read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = PickingTask
        fields = [
            'id', 'task_number', 'order_number', 'picker_name', 'status',
            'zone', 'priority', 'progress_percentage', 'total_items',
            'completed_items', 'assigned_at', 'created_at'
        ]

    def get_progress_percentage(self, obj):
        return obj.progress_percentage


class PickingTaskDetailSerializer(serializers.ModelSerializer):
    """Serializer for picking task details."""

    order_number = serializers.CharField(source='order.order_number', read_only=True)
    picker_name = serializers.CharField(source='picker.username', read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    items = PickingItemSerializer(many=True, read_only=True)

    class Meta:
        model = PickingTask
        fields = [
            'id', 'task_number', 'order_number', 'picker_name', 'status',
            'warehouse_id', 'zone', 'priority', 'progress_percentage',
            'total_items', 'completed_items', 'notes', 'assigned_at',
            'started_at', 'completed_at', 'created_at', 'updated_at',
            'items'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_progress_percentage(self, obj):
        return obj.progress_percentage


class PickingTaskAssignSerializer(serializers.Serializer):
    """Serializer for assigning picker to task."""

    picker_id = serializers.UUIDField()

    def validate_picker_id(self, value):
        """Validate picker exists and is active."""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(id=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive picker")

        return value


class PickingQuantityUpdateSerializer(serializers.Serializer):
    """Serializer for updating picked quantities."""

    item_updates = serializers.ListField(
        child=serializers.DictField(
            child=serializers.DecimalField(max_digits=12, decimal_places=4)
        ),
        allow_empty=False
    )

    def validate_item_updates(self, value):
        """Validate item updates format."""
        for update in value:
            if 'order_item_id' not in update or 'quantity_picked' not in update:
                raise serializers.ValidationError(
                    "Each item update must contain 'order_item_id' and 'quantity_picked'"
                )

            if update['quantity_picked'] < 0:
                raise serializers.ValidationError("Picked quantity cannot be negative")

        return value


class PickingTaskSummarySerializer(serializers.ModelSerializer):
    """Serializer for picking task summary."""

    order_number = serializers.CharField(source='order.order_number', read_only=True)
    picker_name = serializers.CharField(source='picker.username', read_only=True)

    items_summary = serializers.SerializerMethodField()

    class Meta:
        model = PickingTask
        fields = [
            'id', 'task_number', 'order_number', 'picker_name', 'status',
            'progress_percentage', 'total_items', 'completed_items',
            'items_summary', 'assigned_at', 'started_at', 'completed_at'
        ]

    def get_items_summary(self, obj):
        """Get summary of picking items."""
        items = obj.items.all()
        return {
            'total_items': items.count(),
            'completed_items': items.filter(is_completed=True).count(),
            'total_quantity_to_pick': sum(item.quantity_to_pick for item in items),
            'total_quantity_picked': sum(item.quantity_picked for item in items),
        }
