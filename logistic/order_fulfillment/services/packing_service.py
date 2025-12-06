"""
Packing Service for Order Fulfillment & Distribution.

Handles packing task creation, package management, and completion.
"""

import logging
from decimal import Decimal
from typing import List, Dict, Any
from django.db import transaction, models
from django.utils import timezone

from ..models import (
    Order, OrderItem, PackingTask, PackingTaskStatus, Package,
    PackageItem, OrderStatus, AuditLog
)
from ..exceptions import BusinessException, ValidationException
from .workflow import validate_order_workflow, validate_packing_workflow

logger = logging.getLogger(__name__)


class PackingService:
    """Service class for packing operations."""

    @staticmethod
    def create_packing_task(order_id: str, created_by) -> PackingTask:
        """
        Create a packing task for an order ready for packing.

        Args:
            order_id: Order UUID
            created_by: User creating the task

        Returns:
            Created PackingTask instance

        Raises:
            BusinessException: If task cannot be created
        """
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)

            if order.status != OrderStatus.PICKING:
                raise BusinessException(
                    f"Order {order.order_number} must be in picking status to create packing task",
                    "INVALID_ORDER_STATUS"
                )

            # Check if all picking tasks are completed
            incomplete_picking = order.picking_tasks.exclude(status='COMPLETED')
            if incomplete_picking.exists():
                raise BusinessException(
                    f"Cannot create packing task: {incomplete_picking.count()} picking tasks not completed",
                    "INCOMPLETE_PICKING"
                )

            # Check if packing task already exists
            if order.packing_tasks.exists():
                raise BusinessException(
                    f"Packing task already exists for order {order.order_number}",
                    "PACKING_TASK_EXISTS"
                )

            # Count total items to pack
            total_items = order.items.count()

            # Create packing task
            task = PackingTask.objects.create(
                order=order,
                total_items=total_items,
            )

            # Generate unique task number if not set
            if not task.task_number:
                import time
                timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
                task.task_number = f"PAT-{timestamp}-{str(task.id)[:6].upper()}"
                task.save()

            # Update order status
            validate_order_workflow(order, OrderStatus.PACKING)
            old_status = order.status
            order.status = OrderStatus.PACKING
            order.updated_by = created_by
            order.save()

            # Log status change
            AuditLog.log_status_change(
                entity=order,
                old_status=old_status,
                new_status=OrderStatus.PACKING,
                user=created_by,
                notes="Packing task created"
            )

            logger.info(f"Packing task {task.task_number} created for order {order.order_number}")
            return task

    @staticmethod
    def create_package(task_id: str, package_data: Dict[str, Any], created_by) -> Package:
        """
        Create a new package for a packing task.

        Args:
            task_id: Packing task UUID
            package_data: Package specifications
            created_by: User creating the package

        Returns:
            Created Package instance

        Raises:
            ValidationException: If package data is invalid
        """
        with transaction.atomic():
            task = PackingTask.objects.select_for_update().get(id=task_id)

            if task.status not in [PackingTaskStatus.NOT_STARTED, PackingTaskStatus.IN_PROGRESS]:
                raise BusinessException(
                    f"Cannot create package for task {task.task_number} in status {task.status}",
                    "INVALID_TASK_STATUS"
                )

            # Start task if not started
            if task.status == PackingTaskStatus.NOT_STARTED:
                validate_packing_workflow(task, PackingTaskStatus.IN_PROGRESS)
                task.start_packing()

            # Create package
            package = Package.objects.create(
                packing_task=task,
                package_type=package_data.get('package_type', 'BOX'),
                length=package_data.get('length'),
                width=package_data.get('width'),
                height=package_data.get('height'),
                empty_weight=package_data.get('empty_weight', Decimal('0.00')),
                max_weight=package_data.get('max_weight'),
                notes=package_data.get('notes', ''),
                metadata=package_data.get('metadata', {}),
            )

            # Log package creation
            AuditLog.log_change(
                entity=task,
                action='package_created',
                user=created_by,
                new_values={'package_number': package.package_number},
                notes=f"Package {package.package_number} created"
            )

            logger.info(f"Package {package.package_number} created for task {task.task_number}")
            return package

    @staticmethod
    def add_item_to_package(package_id: str, order_item_id: str, quantity: Decimal, added_by) -> PackageItem:
        """
        Add an order item to a package.

        Args:
            package_id: Package UUID
            order_item_id: Order item UUID
            quantity: Quantity to add
            added_by: User adding the item

        Returns:
            Created PackageItem instance

        Raises:
            ValidationException: If addition is invalid
        """
        with transaction.atomic():
            package = Package.objects.select_for_update().get(id=package_id)
            order_item = OrderItem.objects.select_for_update().get(id=order_item_id)

            if package.packing_task.order != order_item.order:
                raise ValidationException("Package and order item must belong to the same order")

            if package.is_sealed:
                raise BusinessException(
                    f"Cannot add items to sealed package {package.package_number}",
                    "PACKAGE_SEALED"
                )

            # Check if item already in package
            existing_item = PackageItem.objects.filter(package=package, order_item=order_item).first()
            if existing_item:
                raise ValidationException(f"Item {order_item.product_sku} already in package {package.package_number}")

            # Validate quantity
            available_to_pack = order_item.quantity_picked - order_item.quantity_packed
            if quantity > available_to_pack:
                raise ValidationException(
                    f"Cannot pack {quantity} of {order_item.product_sku}. "
                    f"Available: {available_to_pack}"
                )

            # Create package item
            package_item = PackageItem.objects.create(
                package=package,
                order_item=order_item,
                quantity=quantity,
            )

            # Update package weight
            item_weight = (quantity * order_item.unit_weight) if order_item.unit_weight else Decimal('0.00')
            package.gross_weight = (package.gross_weight or Decimal('0.00')) + package.empty_weight + item_weight
            package.save()

            # Update order item packed quantity
            order_item.quantity_packed += quantity
            order_item.save()

            # Log addition
            AuditLog.log_change(
                entity=package,
                action='item_added',
                user=added_by,
                new_values={
                    'product_sku': order_item.product_sku,
                    'quantity': quantity
                },
                notes=f"Added {quantity} of {order_item.product_sku} to package"
            )

            return package_item

    @staticmethod
    def finalize_package(package_id: str, finalized_by) -> Package:
        """
        Finalize and seal a package.

        Args:
            package_id: Package UUID
            finalized_by: User finalizing the package

        Returns:
            Finalized Package instance

        Raises:
            BusinessException: If package cannot be finalized
        """
        with transaction.atomic():
            package = Package.objects.select_for_update().prefetch_related('package_items').get(id=package_id)

            if package.is_sealed:
                raise BusinessException(
                    f"Package {package.package_number} is already sealed",
                    "PACKAGE_ALREADY_SEALED"
                )

            if not package.package_items.exists():
                raise BusinessException(
                    f"Cannot seal empty package {package.package_number}",
                    "EMPTY_PACKAGE"
                )

            # Check weight limits
            if package.is_overweight:
                raise ValidationException(
                    f"Package {package.package_number} exceeds maximum weight of {package.max_weight}kg"
                )

            # Seal the package
            package.seal_package()

            # Log sealing
            AuditLog.log_change(
                entity=package,
                action='package_sealed',
                user=finalized_by,
                notes=f"Package sealed with {package.package_items.count()} items"
            )

            logger.info(f"Package {package.package_number} sealed")
            return package

    @staticmethod
    def complete_packing(task_id: str, completed_by) -> PackingTask:
        """
        Complete a packing task.

        Args:
            task_id: Packing task UUID
            completed_by: User completing the task

        Returns:
            Completed PackingTask instance

        Raises:
            BusinessException: If task cannot be completed
        """
        with transaction.atomic():
            task = PackingTask.objects.select_for_update().prefetch_related('packages').get(id=task_id)

            if task.status != PackingTaskStatus.IN_PROGRESS:
                raise BusinessException(
                    f"Task {task.task_number} must be in progress to complete",
                    "INVALID_TASK_STATUS"
                )

            # Check if all order items are packed
            order = task.order
            unpacked_items = order.items.filter(quantity_packed__lt=models.F('quantity_picked'))
            if unpacked_items.exists():
                raise BusinessException(
                    f"Cannot complete packing: {unpacked_items.count()} items not fully packed",
                    "INCOMPLETE_PACKING"
                )

            # Check if all packages are sealed
            unsealed_packages = task.packages.filter(is_sealed=False)
            if unsealed_packages.exists():
                raise BusinessException(
                    f"Cannot complete packing: {unsealed_packages.count()} packages not sealed",
                    "UNSEALED_PACKAGES"
                )

            # Complete the task
            validate_packing_workflow(task, PackingTaskStatus.COMPLETED)
            task.complete_task()

            # Update task progress
            task.completed_items = task.total_items
            task.save()

            # Log completion
            AuditLog.log_status_change(
                entity=task,
                old_status=PackingTaskStatus.IN_PROGRESS,
                new_status=PackingTaskStatus.COMPLETED,
                user=completed_by,
                notes="Packing task completed"
            )

            logger.info(f"Packing task {task.task_number} completed")
            return task

    @staticmethod
    def get_packing_summary(order_id: str) -> Dict[str, Any]:
        """
        Get packing summary for an order.

        Args:
            order_id: Order UUID

        Returns:
            Packing summary
        """
        order = Order.objects.prefetch_related('packing_tasks__packages__package_items').get(id=order_id)

        tasks = order.packing_tasks.all()
        summary = {
            'order_id': order.id,
            'total_tasks': tasks.count(),
            'completed_tasks': tasks.filter(status=PackingTaskStatus.COMPLETED).count(),
            'tasks': []
        }

        for task in tasks:
            task_summary = {
                'task_id': task.id,
                'task_number': task.task_number,
                'status': task.status,
                'packer': task.packer.username if task.packer else None,
                'progress_percentage': task.progress_percentage,
                'packages': []
            }

            for package in task.packages.all():
                package_summary = {
                    'package_id': package.id,
                    'package_number': package.package_number,
                    'package_type': package.package_type,
                    'gross_weight': package.gross_weight,
                    'is_sealed': package.is_sealed,
                    'items': []
                }

                for package_item in package.package_items.all():
                    package_summary['items'].append({
                        'product_sku': package_item.order_item.product_sku,
                        'quantity': package_item.quantity
                    })

                task_summary['packages'].append(package_summary)

            summary['tasks'].append(task_summary)

        return summary
