"""
Shipping Service for Order Fulfillment & Distribution.

Handles shipment creation, carrier assignment, and delivery tracking.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, List
from django.db import transaction
from django.utils import timezone

from ..models import (
    Order, Package, Shipment, ShipmentStatus, ShipmentItem,
    OrderStatus, AuditLog
)
from ..exceptions import BusinessException, ValidationException
from .workflow import validate_order_workflow, validate_shipment_workflow

logger = logging.getLogger(__name__)


class ShippingService:
    """Service class for shipping operations."""

    @staticmethod
    def create_shipment(order_id: str, shipment_data: Dict[str, Any], created_by) -> Shipment:
        """
        Create a shipment for a completed order.

        Args:
            order_id: Order UUID
            shipment_data: Shipment details
            created_by: User creating the shipment

        Returns:
            Created Shipment instance

        Raises:
            BusinessException: If shipment cannot be created
        """
        with transaction.atomic():
            order = Order.objects.select_for_update().prefetch_related('packing_tasks__packages').get(id=order_id)

            if order.status != OrderStatus.PACKING:
                raise BusinessException(
                    f"Order {order.order_number} must be in packing status to create shipment",
                    "INVALID_ORDER_STATUS"
                )

            # Check if all packing tasks are completed
            incomplete_packing = order.packing_tasks.exclude(status='COMPLETED')
            if incomplete_packing.exists():
                raise BusinessException(
                    f"Cannot create shipment: {incomplete_packing.count()} packing tasks not completed",
                    "INCOMPLETE_PACKING"
                )

            # Get all sealed packages
            packages = []
            for task in order.packing_tasks.all():
                packages.extend(task.packages.filter(is_sealed=True))

            if not packages:
                raise BusinessException(
                    f"No sealed packages found for order {order.order_number}",
                    "NO_PACKAGES"
                )

            # Create shipment
            shipment = Shipment.objects.create(
                order=order,
                carrier=shipment_data['carrier'],
                shipping_cost=shipment_data.get('shipping_cost', Decimal('0.00')),
                insurance_cost=shipment_data.get('insurance_cost', Decimal('0.00')),
                ship_from_address=shipment_data.get('ship_from_address', {}),
                ship_to_address=shipment_data.get('ship_to_address', {}),
                estimated_delivery_date=shipment_data.get('estimated_delivery_date'),
                notes=shipment_data.get('notes', ''),
                metadata=shipment_data.get('metadata', {}),
            )

            # Calculate total weight and volume
            total_weight = sum((pkg.gross_weight or Decimal('0.00')) for pkg in packages)
            total_volume = sum((pkg.volume or Decimal('0.00')) for pkg in packages)

            shipment.total_weight = total_weight
            shipment.total_volume = total_volume
            shipment.save()

            # Create shipment items
            for i, package in enumerate(packages, 1):
                ShipmentItem.objects.create(
                    shipment=shipment,
                    package=package,
                    sequence_number=i
                )

            # Update order status
            validate_order_workflow(order, OrderStatus.SHIPPED)
            old_status = order.status
            order.status = OrderStatus.SHIPPED
            order.updated_by = created_by
            order.save()

            # Log status change
            AuditLog.log_status_change(
                entity=order,
                old_status=old_status,
                new_status=OrderStatus.SHIPPED,
                user=created_by,
                notes=f"Shipment {shipment.shipment_number} created with {len(packages)} packages"
            )

            logger.info(f"Shipment {shipment.shipment_number} created for order {order.order_number}")
            return shipment

    @staticmethod
    def assign_tracking(shipment_id: str, tracking_number: str, assigned_by) -> Shipment:
        """
        Assign tracking number to a shipment.

        Args:
            shipment_id: Shipment UUID
            tracking_number: Carrier tracking number
            assigned_by: User assigning tracking

        Returns:
            Updated Shipment instance

        Raises:
            BusinessException: If tracking cannot be assigned
        """
        with transaction.atomic():
            shipment = Shipment.objects.select_for_update().get(id=shipment_id)

            if shipment.tracking_number:
                raise BusinessException(
                    f"Shipment {shipment.shipment_number} already has tracking number assigned",
                    "TRACKING_ALREADY_ASSIGNED"
                )

            shipment.tracking_number = tracking_number
            shipment.save()

            # Log tracking assignment
            AuditLog.log_change(
                entity=shipment,
                action='tracking_assigned',
                user=assigned_by,
                new_values={'tracking_number': tracking_number},
                notes=f"Tracking number {tracking_number} assigned"
            )

            logger.info(f"Tracking number {tracking_number} assigned to shipment {shipment.shipment_number}")
            return shipment

    @staticmethod
    def update_shipment_status(shipment_id: str, new_status: str, status_data: Dict[str, Any], updated_by) -> Shipment:
        """
        Update shipment status in the delivery workflow.

        Args:
            shipment_id: Shipment UUID
            new_status: New status
            status_data: Additional status data (recipient, etc.)
            updated_by: User updating status

        Returns:
            Updated Shipment instance

        Raises:
            BusinessException: If status cannot be updated
        """
        with transaction.atomic():
            shipment = Shipment.objects.select_for_update().get(id=shipment_id)

            # Validate transition
            validate_shipment_workflow(shipment, new_status)

            old_status = shipment.status

            # Handle status-specific updates
            if new_status == ShipmentStatus.LOADED:
                shipment.status = ShipmentStatus.LOADED
                shipment.save()
            elif new_status == ShipmentStatus.DISPATCHED:
                tracking = status_data.get('tracking_number')
                shipment.dispatch_shipment(tracking)
            elif new_status == ShipmentStatus.DELIVERED:
                recipient = status_data.get('recipient_name')
                delivered_by = status_data.get('delivered_by')
                shipment.mark_delivered(recipient, delivered_by)
            elif new_status == ShipmentStatus.CANCELLED:
                shipment.cancel_shipment()
            else:
                # For other statuses, just update
                shipment.status = new_status
                shipment.save()

            # Log status change
            AuditLog.log_status_change(
                entity=shipment,
                old_status=old_status,
                new_status=new_status,
                user=updated_by,
                notes=f"Shipment status updated: {status_data}"
            )

            # If order is delivered, update order status
            if new_status == ShipmentStatus.DELIVERED:
                order = shipment.order
                if order.status == OrderStatus.SHIPPED:
                    validate_order_workflow(order, OrderStatus.DELIVERED)
                    order.status = OrderStatus.DELIVERED
                    order.updated_by = updated_by
                    order.save()

                    AuditLog.log_status_change(
                        entity=order,
                        old_status=OrderStatus.SHIPPED,
                        new_status=OrderStatus.DELIVERED,
                        user=updated_by,
                        notes=f"Order delivered via shipment {shipment.shipment_number}"
                    )

            logger.info(f"Shipment {shipment.shipment_number} status updated to {new_status}")
            return shipment

    @staticmethod
    def generate_manifest(shipment_id: str) -> Dict[str, Any]:
        """
        Generate shipment manifest with package and item details.

        Args:
            shipment_id: Shipment UUID

        Returns:
            Shipment manifest data
        """
        shipment = Shipment.objects.prefetch_related(
            'shipment_items__package__package_items__order_item'
        ).get(id=shipment_id)

        manifest = {
            'shipment_number': shipment.shipment_number,
            'order_number': shipment.order.order_number,
            'carrier': shipment.carrier,
            'tracking_number': shipment.tracking_number,
            'status': shipment.status,
            'ship_from': shipment.ship_from_address,
            'ship_to': shipment.ship_to_address,
            'total_weight': shipment.total_weight,
            'total_volume': shipment.total_volume,
            'estimated_delivery': shipment.estimated_delivery_date,
            'packages': []
        }

        for shipment_item in shipment.shipment_items.all():
            package = shipment_item.package
            package_data = {
                'sequence_number': shipment_item.sequence_number,
                'package_number': package.package_number,
                'package_type': package.package_type,
                'dimensions': {
                    'length': package.length,
                    'width': package.width,
                    'height': package.height,
                },
                'weight': package.gross_weight,
                'items': []
            }

            for package_item in package.package_items.all():
                item = package_item.order_item
                package_data['items'].append({
                    'product_sku': item.product_sku,
                    'product_name': item.product_name,
                    'quantity': package_item.quantity,
                    'unit_price': item.unit_price,
                    'line_total': package_item.quantity * item.unit_price,
                })

            manifest['packages'].append(package_data)

        # Update shipment manifest
        shipment.manifest = manifest
        shipment.save()

        return manifest

    @staticmethod
    def get_shipment_summary(order_id: str) -> Dict[str, Any]:
        """
        Get shipping summary for an order.

        Args:
            order_id: Order UUID

        Returns:
            Shipping summary
        """
        order = Order.objects.prefetch_related('shipments__shipment_items__package').get(id=order_id)

        shipments = order.shipments.all()
        summary = {
            'order_id': order.id,
            'total_shipments': shipments.count(),
            'delivered_shipments': shipments.filter(status=ShipmentStatus.DELIVERED).count(),
            'shipments': []
        }

        for shipment in shipments:
            shipment_summary = {
                'shipment_id': shipment.id,
                'shipment_number': shipment.shipment_number,
                'carrier': shipment.carrier,
                'tracking_number': shipment.tracking_number,
                'status': shipment.status,
                'estimated_delivery': shipment.estimated_delivery_date,
                'actual_delivery': shipment.actual_delivery_date,
                'package_count': shipment.shipment_items.count(),
                'total_weight': shipment.total_weight,
                'shipping_cost': shipment.shipping_cost,
            }
            summary['shipments'].append(shipment_summary)

        return summary
