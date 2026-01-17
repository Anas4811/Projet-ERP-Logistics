"""
Picking Service for Order Fulfillment & Distribution.

Handles picking task creation, assignment, and completion.
"""

import logging
from decimal import Decimal
from typing import List, Dict, Any
from django.db import transaction
from django.utils import timezone

from ..models import (
    Order, OrderItem, PickingTask, PickingTaskStatus, PickingItem,
    OrderStatus, AuditLog
)
from ..exceptions import BusinessException, ValidationException
from .workflow import validate_order_workflow, validate_picking_workflow

logger = logging.getLogger(__name__)


class PickingService:
    """Service class for picking operations."""

    @staticmethod
    def generate_picking_tasks(order_id: str, created_by) -> Dict[str, Any]:
        """
        Generate picking tasks for an allocated order.

        Args:
            order_id: Order UUID
            created_by: User creating the tasks

        Returns:
            Picking tasks creation results

        Raises:
            BusinessException: If tasks cannot be generated
        """
        with transaction.atomic():
            order = Order.objects.select_for_update().prefetch_related('items').get(id=order_id)

            if order.status != OrderStatus.ALLOCATED:
                raise BusinessException(
                    f"Order {order.order_number} must be allocated before generating picking tasks",
                    "INVALID_ORDER_STATUS"
                )

            # Check if picking tasks already exist
            if order.picking_tasks.exists():
                raise BusinessException(
                    f"Picking tasks already exist for order {order.order_number}",
                    "PICKING_TASKS_EXIST"
                )

            # Group items by warehouse and zone for task creation
            task_groups = PickingService._group_items_for_picking(order)

            tasks_created = []
            for group_key, items in task_groups.items():
                warehouse_id, zone = group_key

                # Create picking task
                task = PickingTask.objects.create(
                    order=order,
                    warehouse_id=warehouse_id,
                    zone=zone or '',
                    total_items=len(items),
                )

                # Generate unique task number if not set
                if not task.task_number:
                    import time
                    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
                    task.task_number = f"PT-{timestamp}-{str(task.id)[:6].upper()}"
                    task.save()

                # Create picking items
                for item in items:
                    PickingItem.objects.create(
                        picking_task=task,
                        order_item=item,
                        quantity_to_pick=item.quantity_allocated,  # Pick allocated quantity
                        location=item.allocations.filter(
                            status='RESERVED'
                        ).first().location if item.allocations.exists() else 'UNKNOWN'
                    )

                tasks_created.append(task)

            # Update order status
            validate_order_workflow(order, OrderStatus.PICKING)
            old_status = order.status
            order.status = OrderStatus.PICKING
            order.updated_by = created_by
            order.save()

            # Log status change
            AuditLog.log_status_change(
                entity=order,
                old_status=old_status,
                new_status=OrderStatus.PICKING,
                user=created_by,
                notes=f"Generated {len(tasks_created)} picking tasks"
            )

            logger.info(f"Generated {len(tasks_created)} picking tasks for order {order.order_number}")
            return {
                'success': True,
                'order_id': order.id,
                'tasks_created': len(tasks_created),
                'task_details': [
                    {
                        'task_id': task.id,
                        'task_number': task.task_number,
                        'warehouse_id': task.warehouse_id,
                        'zone': task.zone,
                        'item_count': task.total_items
                    } for task in tasks_created
                ]
            }

    @staticmethod
    def _group_items_for_picking(order: Order) -> Dict[tuple, List[OrderItem]]:
        """
        Group order items for picking task creation.

        Groups by warehouse and zone for efficient picking routes.

        Args:
            order: Order instance

        Returns:
            Dictionary of (warehouse_id, zone) -> [OrderItem]
        """
        groups = {}

        for item in order.items.all():
            # Find primary allocation for location/zone info
            primary_allocation = item.allocations.filter(status='RESERVED').first()

            if primary_allocation:
                warehouse_id = primary_allocation.warehouse_id
                # For now, use location as zone - could be enhanced with zone mapping
                zone = primary_allocation.location.split('-')[0] if '-' in primary_allocation.location else ''
            else:
                # Fallback if no allocation found
                warehouse_id = order.warehouse_id
                zone = ''

            key = (warehouse_id, zone)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)

        return groups

    @staticmethod
    def assign_picker(task_id: str, picker, assigned_by) -> PickingTask:
        """
        Assign a picker to a picking task.

        Args:
            task_id: Picking task UUID
            picker: User to assign as picker
            assigned_by: User making the assignment

        Returns:
            Updated PickingTask instance

        Raises:
            BusinessException: If task cannot be assigned
        """
        with transaction.atomic():
            task = PickingTask.objects.select_for_update().get(id=task_id)

            if task.picker:
                raise BusinessException(
                    f"Task {task.task_number} already has picker assigned",
                    "PICKER_ALREADY_ASSIGNED"
                )

            task.assign_picker(picker)

            # Log assignment
            AuditLog.log_change(
                entity=task,
                action='picker_assigned',
                user=assigned_by,
                new_values={'picker': picker.username},
                notes=f"Picker {picker.username} assigned to task"
            )

            logger.info(f"Picker {picker.username} assigned to task {task.task_number}")
            return task

    @staticmethod
    def update_picked_quantity(task_id: str, item_updates: List[Dict[str, Any]], updated_by) -> Dict[str, Any]:
        """
        Update picked quantities for items in a picking task.

        Args:
            task_id: Picking task UUID
            item_updates: List of {"order_item_id": str, "quantity_picked": Decimal}
            updated_by: User making the update

        Returns:
            Update results

        Raises:
            ValidationException: If quantities are invalid
        """
        with transaction.atomic():
            task = PickingTask.objects.select_for_update().prefetch_related('items').get(id=task_id)

            if task.status not in [PickingTaskStatus.IN_PROGRESS, PickingTaskStatus.NOT_STARTED]:
                raise BusinessException(
                    f"Cannot update picking for task {task.task_number} in status {task.status}",
                    "INVALID_TASK_STATUS"
                )

            # Start task if not started
            if task.status == PickingTaskStatus.NOT_STARTED:
                validate_picking_workflow(task, PickingTaskStatus.IN_PROGRESS)
                task.start_picking()

            updates_applied = []
            validation_errors = []

            # Update each item
            for update in item_updates:
                order_item_id = update['order_item_id']
                quantity_picked = Decimal(str(update['quantity_picked']))

                try:
                    picking_item = task.items.get(order_item_id=order_item_id)

                    # Validate quantity
                    if quantity_picked < 0:
                        raise ValidationException("Picked quantity cannot be negative")

                    if quantity_picked > picking_item.quantity_to_pick:
                        raise ValidationException(
                            f"Picked quantity {quantity_picked} exceeds allocated quantity {picking_item.quantity_to_pick}"
                        )

                    # Update quantities
                    old_picked = picking_item.quantity_picked
                    picking_item.update_picked_quantity(quantity_picked)

                    # Update order item
                    picking_item.order_item.quantity_picked += (quantity_picked - old_picked)
                    picking_item.order_item.save()

                    updates_applied.append({
                        'order_item_id': order_item_id,
                        'quantity_picked': quantity_picked
                    })

                except PickingItem.DoesNotExist:
                    validation_errors.append({
                        'order_item_id': order_item_id,
                        'error': f"Item not found in task {task.task_number}"
                    })
                except ValidationException as e:
                    validation_errors.append({
                        'order_item_id': order_item_id,
                        'error': str(e)
                    })

            # Update task progress
            completed_items = task.items.filter(is_completed=True).count()
            task.completed_items = completed_items
            task.save()

            # Log updates
            AuditLog.log_change(
                entity=task,
                action='quantities_updated',
                user=updated_by,
                notes=f"Updated {len(updates_applied)} items, {len(validation_errors)} errors"
            )

            return {
                'success': len(validation_errors) == 0,
                'task_id': task.id,
                'updates_applied': updates_applied,
                'validation_errors': validation_errors,
                'completed_items': completed_items,
                'total_items': task.total_items
            }

    @staticmethod
    def complete_picking(task_id: str, completed_by) -> PickingTask:
        """
        Mark a picking task as completed.

        Args:
            task_id: Picking task UUID
            completed_by: User completing the task

        Returns:
            Completed PickingTask instance

        Raises:
            BusinessException: If task cannot be completed
        """
        with transaction.atomic():
            task = PickingTask.objects.select_for_update().prefetch_related('items').get(id=task_id)

            if task.status != PickingTaskStatus.IN_PROGRESS:
                raise BusinessException(
                    f"Task {task.task_number} must be in progress to complete",
                    "INVALID_TASK_STATUS"
                )

            # Check if all items are picked
            incomplete_items = task.items.filter(is_completed=False)
            if incomplete_items.exists():
                raise BusinessException(
                    f"Cannot complete task {task.task_number}: {incomplete_items.count()} items not fully picked",
                    "INCOMPLETE_PICKING"
                )

            # Complete the task
            validate_picking_workflow(task, PickingTaskStatus.COMPLETED)
            task.complete_task()

            # Log completion
            AuditLog.log_status_change(
                entity=task,
                old_status=PickingTaskStatus.IN_PROGRESS,
                new_status=PickingTaskStatus.COMPLETED,
                user=completed_by,
                notes="Picking task completed"
            )

            logger.info(f"Picking task {task.task_number} completed")
            return task

    @staticmethod
    def get_picking_summary(order_id: str) -> Dict[str, Any]:
        """
        Get picking summary for an order.

        Args:
            order_id: Order UUID

        Returns:
            Picking summary
        """
        order = Order.objects.prefetch_related('picking_tasks__items').get(id=order_id)

        tasks = order.picking_tasks.all()
        summary = {
            'order_id': order.id,
            'total_tasks': tasks.count(),
            'completed_tasks': tasks.filter(status=PickingTaskStatus.COMPLETED).count(),
            'in_progress_tasks': tasks.filter(status=PickingTaskStatus.IN_PROGRESS).count(),
            'tasks': []
        }

        for task in tasks:
            task_summary = {
                'task_id': task.id,
                'task_number': task.task_number,
                'status': task.status,
                'picker': task.picker.username if task.picker else None,
                'progress_percentage': task.progress_percentage,
                'completed_items': task.completed_items,
                'total_items': task.total_items,
                'items': []
            }

            for item in task.items.all():
                task_summary['items'].append({
                    'order_item_id': item.order_item.id,
                    'product_sku': item.order_item.product_sku,
                    'quantity_to_pick': item.quantity_to_pick,
                    'quantity_picked': item.quantity_picked,
                    'is_completed': item.is_completed
                })

            summary['tasks'].append(task_summary)

        return summary
