"""
Order Service for Order Fulfillment & Distribution.

Handles order lifecycle operations including creation, approval, and status updates.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, List
from django.db import transaction
from django.utils import timezone

from ..models import Order, OrderItem, OrderStatus, AuditLog
from ..exceptions import BusinessException, ValidationException
from .workflow import validate_order_workflow

logger = logging.getLogger(__name__)


class OrderService:
    """Service class for order operations."""

    @staticmethod
    def create_order(customer, order_data: Dict[str, Any], created_by=None) -> Order:
        """
        Create a new order with items.

        Args:
            customer: Customer user instance
            order_data: Order data including items, warehouse_id, etc.
            created_by: User creating the order

        Returns:
            Created Order instance

        Raises:
            ValidationException: If order data is invalid
        """
        with transaction.atomic():
            # Create order
            order = Order.objects.create(
                customer=customer,
                warehouse_id=order_data.get('warehouse_id'),
                priority=order_data.get('priority', 'MEDIUM'),
                notes=order_data.get('notes', ''),
                metadata=order_data.get('metadata', {}),
                created_by=created_by,
                updated_by=created_by,
            )

            # Create order items
            items_data = order_data.get('items', [])
            if not items_data:
                raise ValidationException("Order must contain at least one item")

            total_amount = Decimal('0.00')
            for item_data in items_data:
                item = OrderItem.objects.create(
                    order=order,
                    product_id=item_data['product_id'],
                    product_sku=item_data['product_sku'],
                    product_name=item_data['product_name'],
                    quantity_ordered=item_data['quantity'],
                    unit_price=item_data['unit_price'],
                    unit_weight=item_data.get('unit_weight'),
                    metadata=item_data.get('metadata', {}),
                )
                total_amount += item.line_total

            # Update order totals
            order.subtotal = total_amount
            order.total_amount = total_amount  # Will be recalculated with taxes/shipping if needed
            order.save()

            # Log creation
            AuditLog.log_change(
                entity=order,
                action='created',
                user=created_by,
                new_values={'status': OrderStatus.CREATED},
                notes=f"Order created with {len(items_data)} items"
            )

            logger.info(f"Order {order.order_number} created for customer {customer}")
            return order

    @staticmethod
    def approve_order(order_id: str, approved_by) -> Order:
        """
        Approve an order for fulfillment processing.

        Args:
            order_id: Order UUID
            approved_by: User approving the order

        Returns:
            Updated Order instance

        Raises:
            BusinessException: If order cannot be approved
        """
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)

            if order.status != OrderStatus.CREATED:
                raise BusinessException(
                    f"Order {order.order_number} cannot be approved from status {order.status}",
                    "INVALID_ORDER_STATUS"
                )

            # Validate transition
            validate_order_workflow(order, OrderStatus.APPROVED)

            # Update order
            old_status = order.status
            order.status = OrderStatus.APPROVED
            order.updated_by = approved_by
            order.save()

            # Log status change
            AuditLog.log_status_change(
                entity=order,
                old_status=old_status,
                new_status=OrderStatus.APPROVED,
                user=approved_by,
                notes="Order approved for fulfillment"
            )

            logger.info(f"Order {order.order_number} approved by {approved_by}")
            return order

    @staticmethod
    def calculate_totals(order: Order) -> Dict[str, Decimal]:
        """
        Recalculate order totals based on items.

        Args:
            order: Order instance

        Returns:
            Dictionary with calculated totals
        """
        subtotal = Decimal('0.00')
        total_weight = Decimal('0.00')

        for item in order.items.all():
            subtotal += item.line_total
            if item.total_weight:
                total_weight += item.total_weight

        tax_amount = order.tax_amount or Decimal('0.00')
        shipping_amount = order.shipping_amount or Decimal('0.00')
        total_amount = subtotal + tax_amount + shipping_amount

        return {
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'shipping_amount': shipping_amount,
            'total_amount': total_amount,
            'total_weight': total_weight,
        }

    @staticmethod
    def update_order(order_id: str, update_data: Dict[str, Any], updated_by) -> Order:
        """
        Update order information.

        Args:
            order_id: Order UUID
            update_data: Fields to update
            updated_by: User making the update

        Returns:
            Updated Order instance

        Raises:
            BusinessException: If order cannot be updated
        """
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)

            # Prevent updates to orders that are too far in the process
            if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
                raise BusinessException(
                    f"Order {order.order_number} cannot be updated in status {order.status}",
                    "ORDER_NOT_UPDATABLE"
                )

            old_values = {}
            new_values = {}

            # Update allowed fields
            updatable_fields = ['priority', 'notes', 'metadata', 'tax_amount', 'shipping_amount']
            for field in updatable_fields:
                if field in update_data:
                    old_values[field] = getattr(order, field)
                    setattr(order, field, update_data[field])
                    new_values[field] = update_data[field]

            # Recalculate totals if financial fields changed
            if any(field in update_data for field in ['tax_amount', 'shipping_amount']):
                totals = OrderService.calculate_totals(order)
                order.total_amount = totals['total_amount']

            order.updated_by = updated_by
            order.save()

            # Log changes
            if old_values:
                AuditLog.log_change(
                    entity=order,
                    action='updated',
                    user=updated_by,
                    old_values=old_values,
                    new_values=new_values,
                    notes="Order information updated"
                )

            logger.info(f"Order {order.order_number} updated by {updated_by}")
            return order

    @staticmethod
    def cancel_order(order_id: str, cancelled_by, reason: str = "") -> Order:
        """
        Cancel an order.

        Args:
            order_id: Order UUID
            cancelled_by: User cancelling the order
            reason: Cancellation reason

        Returns:
            Cancelled Order instance

        Raises:
            BusinessException: If order cannot be cancelled
        """
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)

            if not order.can_be_cancelled:
                raise BusinessException(
                    f"Order {order.order_number} cannot be cancelled from status {order.status}",
                    "ORDER_NOT_CANCELLABLE"
                )

            # Validate transition
            validate_order_workflow(order, OrderStatus.CANCELLED)

            # Update order
            old_status = order.status
            order.status = OrderStatus.CANCELLED
            order.updated_by = cancelled_by
            order.save()

            # Log status change
            AuditLog.log_status_change(
                entity=order,
                old_status=old_status,
                new_status=OrderStatus.CANCELLED,
                user=cancelled_by,
                notes=f"Order cancelled: {reason}"
            )

            logger.info(f"Order {order.order_number} cancelled by {cancelled_by}")
            return order

    @staticmethod
    def get_order_summary(order_id: str) -> Dict[str, Any]:
        """
        Get comprehensive order summary.

        Args:
            order_id: Order UUID

        Returns:
            Order summary with items, allocations, tasks, etc.
        """
        order = Order.objects.select_related('customer').prefetch_related(
            'items', 'allocations', 'picking_tasks', 'packing_tasks', 'shipments'
        ).get(id=order_id)

        items_summary = []
        for item in order.items.all():
            allocations = item.allocations.filter(status='RESERVED')
            total_allocated = sum(a.quantity_reserved for a in allocations)

            items_summary.append({
                'id': item.id,
                'product_sku': item.product_sku,
                'product_name': item.product_name,
                'quantity_ordered': item.quantity_ordered,
                'quantity_allocated': total_allocated,
                'quantity_picked': item.quantity_picked,
                'quantity_packed': item.quantity_packed,
                'quantity_shipped': item.quantity_shipped,
            })

        return {
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'status': order.status,
                'priority': order.priority,
                'total_amount': order.total_amount,
                'created_at': order.created_at,
                'customer': order.customer.username,
            },
            'items': items_summary,
            'picking_tasks_count': order.picking_tasks.count(),
            'packing_tasks_count': order.packing_tasks.count(),
            'shipments_count': order.shipments.count(),
        }
