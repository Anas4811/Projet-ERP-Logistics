"""
Tests for complete Order Fulfillment flow.
"""

import uuid
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import Order, OrderItem, OrderStatus, ShipmentStatus
from ..services import OrderService, AllocationService, PickingService, PackingService, ShippingService
from ..adapters.inventory_adapter import switch_to_mock_adapter


class OrderFulfillmentFlowTest(TestCase):
    """Test complete order fulfillment workflow."""

    def setUp(self):
        """Set up test data."""
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Switch to mock inventory adapter
        switch_to_mock_adapter()

    def test_complete_order_fulfillment_flow(self):
        """Test complete order fulfillment from creation to delivery."""

        # 1. Create order
        order_data = {
            'warehouse_id': '11111111-1111-1111-1111-111111111111',  # Use known warehouse ID from mock
            'items': [
                {
                    'product_id': str(uuid.uuid4()),
                    'product_sku': 'PROD-001',
                    'product_name': 'Test Product 1',
                    'quantity': Decimal('10.0000'),
                    'unit_price': Decimal('25.50'),
                    'unit_weight': Decimal('1.5'),
                },
                {
                    'product_id': str(uuid.uuid4()),
                    'product_sku': 'PROD-002',
                    'product_name': 'Test Product 2',
                    'quantity': Decimal('5.0000'),
                    'unit_price': Decimal('15.75'),
                    'unit_weight': Decimal('0.8'),
                }
            ]
        }

        order = OrderService.create_order(self.user, order_data, self.user)
        self.assertEqual(order.status, OrderStatus.CREATED)
        self.assertEqual(order.items.count(), 2)

        # Verify order totals
        expected_subtotal = Decimal('10') * Decimal('25.50') + Decimal('5') * Decimal('15.75')
        self.assertEqual(order.subtotal, expected_subtotal)

        # 2. Approve order
        approved_order = OrderService.approve_order(str(order.id), self.user)
        self.assertEqual(approved_order.status, OrderStatus.APPROVED)

        # 3. Allocate inventory
        allocation_result = AllocationService.allocate(str(order.id), self.user)
        self.assertTrue(allocation_result['success'])
        self.assertEqual(allocation_result['allocations_created'], 2)  # One allocation per item

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.ALLOCATED)

        # Verify allocations
        allocations = order.allocations.all()
        self.assertEqual(allocations.count(), 2)
        for allocation in allocations:
            self.assertEqual(allocation.status, 'RESERVED')

        # 4. Generate picking tasks
        picking_result = PickingService.generate_picking_tasks(str(order.id), self.user)
        self.assertTrue(picking_result['success'])
        self.assertEqual(picking_result['tasks_created'], 2)  # Grouped by zone (A and B)

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PICKING)

        # Check that picking tasks were created
        self.assertEqual(order.picking_tasks.count(), 2)
        # Each task should have 1 item (grouped by zone)
        for task in order.picking_tasks.all():
            self.assertEqual(task.total_items, 1)

        # 5. Assign picker and update picking for each task
        from django.contrib.auth import get_user_model
        picker = get_user_model().objects.create_user(
            username='picker',
            email='picker@example.com',
            password='testpass123'
        )

        # Process each picking task
        for picking_task in order.picking_tasks.all():
            assigned_task = PickingService.assign_picker(str(picking_task.id), picker, self.user)
            self.assertEqual(assigned_task.picker, picker)

            # Update picked quantities for items in this task
            item_updates = []
            for picking_item in picking_task.items.all():
                item_updates.append({
                    'order_item_id': str(picking_item.order_item.id),
                    'quantity_picked': picking_item.quantity_to_pick
                })

            picking_result = PickingService.update_picked_quantity(
                str(picking_task.id), item_updates, self.user
            )
            self.assertTrue(picking_result['success'])

            # Complete picking
            completed_task = PickingService.complete_picking(str(picking_task.id), self.user)
            self.assertEqual(completed_task.status, 'COMPLETED')

        # 6. Create packing task
        packing_task = PackingService.create_packing_task(str(order.id), self.user)
        self.assertEqual(packing_task.status, 'NOT_STARTED')

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PACKING)

        # 7. Create package and add items
        package_data = {
            'package_type': 'BOX',
            'length': Decimal('30.0'),
            'width': Decimal('20.0'),
            'height': Decimal('15.0'),
            'empty_weight': Decimal('0.5'),
            'max_weight': Decimal('25.0'),
        }

        package = PackingService.create_package(str(packing_task.id), package_data, self.user)

        # Add items to package
        for item in order.items.all():
            PackingService.add_item_to_package(
                str(package.id), str(item.id), item.quantity_picked, self.user
            )

        # Finalize package
        finalized_package = PackingService.finalize_package(str(package.id), self.user)
        self.assertTrue(finalized_package.is_sealed)

        # Complete packing
        completed_packing = PackingService.complete_packing(str(packing_task.id), self.user)
        self.assertEqual(completed_packing.status, 'COMPLETED')

        # 8. Create shipment
        shipment_data = {
            'carrier': 'FedEx',
            'shipping_cost': Decimal('15.99'),
            'ship_from_address': {
                'street': '123 Warehouse St',
                'city': 'Warehouse City',
                'country': 'US',
                'postal_code': '12345'
            },
            'ship_to_address': {
                'street': '456 Customer Ave',
                'city': 'Customer City',
                'country': 'US',
                'postal_code': '67890'
            },
            'estimated_delivery_date': timezone.now() + timezone.timedelta(days=3)
        }

        shipment = ShippingService.create_shipment(str(order.id), shipment_data, self.user)
        self.assertEqual(shipment.status, 'CREATED')
        self.assertEqual(shipment.shipment_items.count(), 1)  # One package

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.SHIPPED)

        # 9. Update shipment status through proper workflow
        # CREATED -> LOADED
        loaded_shipment = ShippingService.update_shipment_status(
            str(shipment.id), 'LOADED', {}, self.user
        )
        self.assertEqual(loaded_shipment.status, 'LOADED')

        # LOADED -> DISPATCHED
        dispatched_shipment = ShippingService.update_shipment_status(
            str(shipment.id), 'DISPATCHED',
            {'tracking_number': 'TRK123456789'}, self.user
        )
        self.assertEqual(dispatched_shipment.status, 'DISPATCHED')

        # DISPATCHED -> IN_TRANSIT
        in_transit_shipment = ShippingService.update_shipment_status(
            str(shipment.id), 'IN_TRANSIT', {}, self.user
        )
        self.assertEqual(in_transit_shipment.status, 'IN_TRANSIT')

        # IN_TRANSIT -> OUT_FOR_DELIVERY
        out_for_delivery_shipment = ShippingService.update_shipment_status(
            str(shipment.id), 'OUT_FOR_DELIVERY', {}, self.user
        )
        self.assertEqual(out_for_delivery_shipment.status, 'OUT_FOR_DELIVERY')

        # OUT_FOR_DELIVERY -> DELIVERED
        delivered_shipment = ShippingService.update_shipment_status(
            str(shipment.id), 'DELIVERED',
            {'recipient_name': 'John Doe', 'delivered_by': 'FedEx Driver'}, self.user
        )
        self.assertEqual(delivered_shipment.status, ShipmentStatus.DELIVERED)

        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.DELIVERED)

        # Verify final state
        self.assertTrue(order.is_delivered)
        self.assertEqual(delivered_shipment.status, ShipmentStatus.DELIVERED)
