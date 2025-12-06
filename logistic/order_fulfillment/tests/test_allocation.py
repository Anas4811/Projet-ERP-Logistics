"""
Tests for inventory allocation functionality.
"""

import uuid
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from ..models import Order, OrderItem, OrderStatus, Allocation
from ..services import OrderService, AllocationService
from ..exceptions import AllocationException, InventoryUnavailableException
from ..adapters.inventory_adapter import MockInventoryAdapter, switch_to_mock_adapter


class AllocationTest(TestCase):
    """Test allocation service functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Switch to mock inventory adapter
        switch_to_mock_adapter()

    def _create_approved_order_with_available_items(self):
        """Create an order with items that have available inventory."""
        order = OrderService.create_order(
            self.user,
            {
                'warehouse_id': '11111111-1111-1111-1111-111111111111',
                'items': [
                    {
                        'product_id': str(uuid.uuid4()),
                        'product_sku': 'PROD-001',  # Available in mock
                        'product_name': 'Test Product 1',
                        'quantity': Decimal('5.0000'),
                        'unit_price': Decimal('10.00'),
                    },
                    {
                        'product_id': str(uuid.uuid4()),
                        'product_sku': 'PROD-002',  # Available in mock
                        'product_name': 'Test Product 2',
                        'quantity': Decimal('10.0000'),
                        'unit_price': Decimal('15.00'),
                    }
                ]
            },
            self.user
        )
        OrderService.approve_order(str(order.id), self.user)
        return order

    def _create_approved_order_with_insufficient_stock(self):
        """Create an order with items that exceed available inventory."""
        order = OrderService.create_order(
            self.user,
            {
                'warehouse_id': '11111111-1111-1111-1111-111111111111',
                'items': [
                    {
                        'product_id': str(uuid.uuid4()),
                        'product_sku': 'PROD-003',  # Limited stock in mock (25 available)
                        'product_name': 'Test Product',
                        'quantity': Decimal('30.0000'),  # More than available
                        'unit_price': Decimal('15.00'),
                    }
                ]
            },
            self.user
        )
        OrderService.approve_order(str(order.id), self.user)
        return order

    def test_successful_allocation(self):
        """Test successful inventory allocation."""
        order = self._create_approved_order_with_available_items()

        # Allocate inventory
        result = AllocationService.allocate(str(order.id), self.user)

        self.assertTrue(result['success'])
        self.assertEqual(result['allocations_created'], 2)  # Both items should be allocated

        # Check order status
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.ALLOCATED)

        # Check allocations
        allocations = Allocation.objects.filter(order=order)
        self.assertEqual(allocations.count(), 2)

        # Check that allocations have correct quantities
        prod001_allocation = allocations.filter(order_item__product_sku='PROD-001').first()
        prod002_allocation = allocations.filter(order_item__product_sku='PROD-002').first()

        self.assertEqual(prod001_allocation.quantity_reserved, Decimal('5.0000'))
        self.assertEqual(prod002_allocation.quantity_reserved, Decimal('10.0000'))

        for allocation in allocations:
            self.assertEqual(allocation.status, 'RESERVED')

        # Check order item allocations
        prod001_item = OrderItem.objects.get(order=order, product_sku='PROD-001')
        prod002_item = OrderItem.objects.get(order=order, product_sku='PROD-002')

        self.assertEqual(prod001_item.quantity_allocated, Decimal('5.0000'))
        self.assertEqual(prod002_item.quantity_allocated, Decimal('10.0000'))

    def test_insufficient_inventory_allocation(self):
        """Test allocation failure due to insufficient inventory."""
        order = self._create_approved_order_with_insufficient_stock()

        # This should fail because PROD-003 only has 25 units available
        # but we're trying to allocate 30
        with self.assertRaises(AllocationException):
            AllocationService.allocate(str(order.id), self.user)

    def test_allocation_validation(self):
        """Test allocation validation."""
        order = self._create_approved_order_with_available_items()

        # Test validation of already allocated order
        AllocationService.allocate(str(order.id), self.user)

        # Try to allocate again
        with self.assertRaises(Exception):  # Should raise BusinessException
            AllocationService.allocate(str(order.id), self.user)

    def test_release_allocations(self):
        """Test allocation release."""
        order = self._create_approved_order_with_available_items()

        # First allocate
        AllocationService.allocate(str(order.id), self.user)

        # Release allocations
        result = AllocationService.release_allocations(str(order.id), self.user)

        self.assertTrue(result['released_count'] > 0)

        # Check allocations are released
        allocations = Allocation.objects.filter(order=order)
        for allocation in allocations:
            self.assertEqual(allocation.status, 'RELEASED')

        # Check order items
        for item in order.items.all():
            self.assertEqual(item.quantity_allocated, Decimal('0.0000'))

    def test_allocation_summary(self):
        """Test allocation summary generation."""
        order = self._create_approved_order_with_available_items()

        # Allocate
        AllocationService.allocate(str(order.id), self.user)

        # Get summary
        summary = AllocationService.get_allocation_summary(str(order.id))

        self.assertIn('order_id', summary)
        self.assertIn('total_allocations', summary)
        self.assertIn('allocations_by_location', summary)
        self.assertIn('allocations_by_item', summary)

        self.assertEqual(summary['total_allocations'], 2)

    def test_invalid_order_status_allocation(self):
        """Test allocation on order with invalid status."""

        # Create order but don't approve it
        new_order = OrderService.create_order(
            self.user,
            {
                'warehouse_id': str(uuid.uuid4()),
                'items': [{
                    'product_id': str(uuid.uuid4()),
                    'product_sku': 'PROD-001',
                    'product_name': 'Test Product',
                    'quantity': Decimal('1.0000'),
                    'unit_price': Decimal('10.00'),
                }]
            },
            self.user
        )

        # Try to allocate without approval
        with self.assertRaises(Exception):  # Should raise BusinessException
            AllocationService.allocate(str(new_order.id), self.user)


class MockInventoryAdapterTest(TestCase):
    """Test the mock inventory adapter."""

    def setUp(self):
        """Set up mock adapter."""
        self.adapter = MockInventoryAdapter()

    def test_check_availability_success(self):
        """Test successful availability check."""

        result = self.adapter.check_availability('PROD-001', Decimal('5.0'), uuid.UUID('11111111-1111-1111-1111-111111111111'))

        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIn('location', result[0])
        self.assertIn('available', result[0])

    def test_check_availability_insufficient(self):
        """Test availability check with insufficient inventory."""

        with self.assertRaises(InventoryUnavailableException):
            self.adapter.check_availability('PROD-003', Decimal('50.0'), uuid.UUID('11111111-1111-1111-1111-111111111111'))

    def test_reserve_inventory(self):
        """Test inventory reservation."""

        result = self.adapter.reserve('PROD-001', Decimal('5.0'), 'A-01-01', 'TEST-REF')

        self.assertIn('reservation_id', result)
        self.assertEqual(result['reserved_qty'], Decimal('5.0'))

    def test_release_inventory(self):
        """Test inventory release."""

        # First reserve
        reservation = self.adapter.reserve('PROD-001', Decimal('5.0'), 'A-01-01', 'TEST-REF')

        # Then release
        result = self.adapter.release(reservation['reservation_id'])
        self.assertTrue(result)
