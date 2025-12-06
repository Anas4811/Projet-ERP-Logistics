"""
Allocation Service for Order Fulfillment & Distribution.

Handles inventory allocation and reservation for orders.
"""

import logging
from decimal import Decimal
from typing import List, Dict, Any
from django.db import transaction
from django.utils import timezone

from ..models import Order, OrderItem, Allocation, AllocationStatus, OrderStatus, AuditLog
from ..exceptions import BusinessException, AllocationException
from ..adapters.inventory_adapter import get_inventory_adapter
from .workflow import validate_order_workflow

logger = logging.getLogger(__name__)


class AllocationService:
    """Service class for inventory allocation operations."""

    @staticmethod
    def allocate(order_id: str, allocated_by) -> Dict[str, Any]:
        """
        Allocate inventory for an approved order.

        Args:
            order_id: Order UUID
            allocated_by: User performing allocation

        Returns:
            Allocation results with success/failure details

        Raises:
            BusinessException: If order cannot be allocated
            AllocationException: If allocation fails
        """
        with transaction.atomic():
            order = Order.objects.select_for_update().prefetch_related('items').get(id=order_id)

            if order.status != OrderStatus.APPROVED:
                raise BusinessException(
                    f"Order {order.order_number} must be approved before allocation",
                    "INVALID_ORDER_STATUS"
                )

            # Check if already allocated
            if order.is_allocated:
                raise BusinessException(
                    f"Order {order.order_number} is already allocated",
                    "ORDER_ALREADY_ALLOCATED"
                )

            inventory_adapter = get_inventory_adapter()
            allocations_created = []
            allocation_failures = []

            # Allocate each order item
            for item in order.items.all():
                try:
                    item_allocations = AllocationService._allocate_order_item(
                        item, order.warehouse_id, inventory_adapter
                    )
                    allocations_created.extend(item_allocations)
                except Exception as e:
                    logger.error(f"Failed to allocate item {item.product_sku}: {str(e)}")
                    allocation_failures.append({
                        'item_id': item.id,
                        'product_sku': item.product_sku,
                        'error': str(e)
                    })

            # If any allocations failed, rollback all
            if allocation_failures:
                # Release any allocations that were created
                for allocation in allocations_created:
                    try:
                        inventory_adapter.release(allocation.reservation_id)
                        allocation.release()
                    except Exception as e:
                        logger.error(f"Failed to release allocation {allocation.reservation_id}: {str(e)}")

                raise AllocationException(
                    f"Failed to allocate {len(allocation_failures)} items for order {order.order_number}",
                    {"allocation_failures": allocation_failures}
                )

            # Update order status
            validate_order_workflow(order, OrderStatus.ALLOCATED)
            old_status = order.status
            order.status = OrderStatus.ALLOCATED
            order.updated_by = allocated_by
            order.save()

            # Log status change
            AuditLog.log_status_change(
                entity=order,
                old_status=old_status,
                new_status=OrderStatus.ALLOCATED,
                user=allocated_by,
                notes=f"Inventory allocated for {len(allocations_created)} items"
            )

            logger.info(f"Order {order.order_number} allocated with {len(allocations_created)} allocations")
            return {
                'success': True,
                'order_id': order.id,
                'allocations_created': len(allocations_created),
                'allocation_details': [
                    {
                        'item_sku': alloc.order_item.product_sku,
                        'location': alloc.location,
                        'quantity': alloc.quantity_reserved
                    } for alloc in allocations_created
                ]
            }

    @staticmethod
    def _allocate_order_item(item: OrderItem, warehouse_id, inventory_adapter) -> List[Allocation]:
        """
        Allocate inventory for a single order item.

        Args:
            item: OrderItem to allocate
            warehouse_id: Warehouse UUID
            inventory_adapter: Inventory adapter instance

        Returns:
            List of created Allocation instances

        Raises:
            AllocationException: If allocation fails
        """
        remaining_qty = item.remaining_to_allocate

        if remaining_qty <= 0:
            return []  # Already fully allocated

        # Check inventory availability
        available_locations = inventory_adapter.check_availability(
            sku=item.product_sku,
            qty=remaining_qty,
            warehouse_id=warehouse_id
        )

        allocations = []
        qty_to_allocate = remaining_qty

        # Allocate from available locations
        for location_info in available_locations:
            if qty_to_allocate <= 0:
                break

            location = location_info['location']
            available_qty = location_info['available']
            allocate_qty = min(qty_to_allocate, available_qty)

            # Reserve in inventory system
            reservation_result = inventory_adapter.reserve(
                sku=item.product_sku,
                qty=allocate_qty,
                location=location,
                reference=f"ORDER-{item.order.order_number}"
            )

            # Create allocation record
            allocation = Allocation.objects.create(
                order=item.order,
                order_item=item,
                warehouse_id=warehouse_id,
                location=location,
                quantity_reserved=allocate_qty,
                reservation_id=reservation_result['reservation_id'],
            )

            allocations.append(allocation)
            qty_to_allocate -= allocate_qty

            # Update item allocation quantity
            item.quantity_allocated += allocate_qty
            item.save()

        if qty_to_allocate > 0:
            # Could not allocate full quantity
            raise AllocationException(
                f"Could not allocate full quantity for {item.product_sku}. "
                f"Requested: {remaining_qty}, allocated: {remaining_qty - qty_to_allocate}"
            )

        return allocations

    @staticmethod
    def release_allocations(order_id: str, released_by=None) -> Dict[str, Any]:
        """
        Release all allocations for an order.

        Args:
            order_id: Order UUID
            released_by: User releasing allocations

        Returns:
            Release results

        Raises:
            BusinessException: If allocations cannot be released
        """
        with transaction.atomic():
            order = Order.objects.select_for_update().prefetch_related('allocations').get(id=order_id)

            # Only allow release for orders that haven't progressed too far
            if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
                raise BusinessException(
                    f"Cannot release allocations for order {order.order_number} in status {order.status}",
                    "ALLOCATION_NOT_RELEASABLE"
                )

            inventory_adapter = get_inventory_adapter()
            released_count = 0
            release_failures = []

            # Release allocations
            for allocation in order.allocations.filter(status=AllocationStatus.RESERVED):
                try:
                    # Release in inventory system
                    inventory_adapter.release(allocation.reservation_id)

                    # Update allocation record
                    allocation.release()

                    # Update order item
                    allocation.order_item.quantity_allocated -= allocation.quantity_reserved
                    allocation.order_item.save()

                    released_count += 1

                except Exception as e:
                    logger.error(f"Failed to release allocation {allocation.reservation_id}: {str(e)}")
                    release_failures.append({
                        'allocation_id': allocation.id,
                        'reservation_id': allocation.reservation_id,
                        'error': str(e)
                    })

            # Log the release
            AuditLog.log_change(
                entity=order,
                action='allocations_released',
                user=released_by,
                notes=f"Released {released_count} allocations"
            )

            logger.info(f"Released {released_count} allocations for order {order.order_number}")
            return {
                'success': True,
                'released_count': released_count,
                'release_failures': release_failures
            }

    @staticmethod
    def validate_allocation(order_id: str) -> Dict[str, Any]:
        """
        Validate that an order's allocation is still valid.

        Args:
            order_id: Order UUID

        Returns:
            Validation results
        """
        order = Order.objects.prefetch_related('items__allocations').get(id=order_id)

        validation_results = {
            'order_id': order.id,
            'is_valid': True,
            'issues': []
        }

        for item in order.items.all():
            allocated_qty = item.quantity_allocated
            ordered_qty = item.quantity_ordered

            if allocated_qty < ordered_qty:
                validation_results['is_valid'] = False
                validation_results['issues'].append({
                    'item_id': item.id,
                    'product_sku': item.product_sku,
                    'ordered': ordered_qty,
                    'allocated': allocated_qty,
                    'shortage': ordered_qty - allocated_qty
                })

        return validation_results

    @staticmethod
    def get_allocation_summary(order_id: str) -> Dict[str, Any]:
        """
        Get allocation summary for an order.

        Args:
            order_id: Order UUID

        Returns:
            Allocation summary
        """
        order = Order.objects.prefetch_related('allocations__order_item').get(id=order_id)

        allocations = order.allocations.filter(status=AllocationStatus.RESERVED)

        summary = {
            'order_id': order.id,
            'total_allocations': allocations.count(),
            'allocations_by_location': {},
            'allocations_by_item': {}
        }

        for allocation in allocations:
            # By location
            location = allocation.location
            if location not in summary['allocations_by_location']:
                summary['allocations_by_location'][location] = {
                    'total_quantity': Decimal('0.0000'),
                    'items': []
                }

            summary['allocations_by_location'][location]['total_quantity'] += allocation.quantity_reserved
            summary['allocations_by_location'][location]['items'].append({
                'sku': allocation.order_item.product_sku,
                'quantity': allocation.quantity_reserved
            })

            # By item
            item_sku = allocation.order_item.product_sku
            if item_sku not in summary['allocations_by_item']:
                summary['allocations_by_item'][item_sku] = {
                    'total_quantity': Decimal('0.0000'),
                    'locations': []
                }

            summary['allocations_by_item'][item_sku]['total_quantity'] += allocation.quantity_reserved
            summary['allocations_by_item'][item_sku]['locations'].append({
                'location': location,
                'quantity': allocation.quantity_reserved
            })

        return summary
