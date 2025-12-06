"""
Inventory Adapter for Order Fulfillment & Distribution.

Provides interface to inventory management system with deterministic mock implementation.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import UUID

from ..exceptions import InventoryUnavailableException


class InventoryAdapterInterface(ABC):
    """
    Interface for inventory management system integration.

    This abstract base class defines the contract for inventory operations
    that the Order Fulfillment system needs.
    """

    @abstractmethod
    def check_availability(self, sku: str, qty: Decimal, warehouse_id: UUID) -> List[Dict[str, Any]]:
        """
        Check availability of a product in a specific warehouse.

        Args:
            sku: Product SKU to check
            qty: Quantity needed
            warehouse_id: Warehouse to check inventory in

        Returns:
            List of available locations with quantities:
            [{"location": str, "available": Decimal}, ...]

        Raises:
            InventoryUnavailableException: If insufficient inventory
        """
        pass

    @abstractmethod
    def reserve(self, sku: str, qty: Decimal, location: str, reference: str) -> Dict[str, Any]:
        """
        Reserve inventory at a specific location.

        Args:
            sku: Product SKU to reserve
            qty: Quantity to reserve
            location: Warehouse location
            reference: Reference for the reservation (e.g., order number)

        Returns:
            Reservation details:
            {"reservation_id": str, "reserved_qty": Decimal}

        Raises:
            InventoryUnavailableException: If inventory cannot be reserved
        """
        pass

    @abstractmethod
    def release(self, reservation_id: str) -> bool:
        """
        Release a reservation.

        Args:
            reservation_id: ID of reservation to release

        Returns:
            True if reservation was released successfully

        Raises:
            InventoryUnavailableException: If reservation cannot be released
        """
        pass


class MockInventoryAdapter(InventoryAdapterInterface):
    """
    Deterministic mock implementation for testing and development.

    Provides predictable inventory responses for testing the Order Fulfillment system.
    """

    def __init__(self):
        # Mock inventory data - deterministic for testing
        self.mock_inventory = {
            # Format: (warehouse_id, sku) -> [{"location": str, "available": Decimal}, ...]
            (UUID('11111111-1111-1111-1111-111111111111'), 'PROD-001'): [
                {"location": "A-01-01", "available": Decimal('100.0000')},
                {"location": "A-01-02", "available": Decimal('50.0000')},
            ],
            (UUID('11111111-1111-1111-1111-111111111111'), 'PROD-002'): [
                {"location": "B-02-01", "available": Decimal('75.0000')},
            ],
            (UUID('11111111-1111-1111-1111-111111111111'), 'PROD-003'): [
                {"location": "C-03-01", "available": Decimal('25.0000')},  # Limited stock
            ],
            (UUID('22222222-2222-2222-2222-222222222222'), 'PROD-001'): [
                {"location": "A-01-01", "available": Decimal('200.0000')},
            ],
            (UUID('22222222-2222-2222-2222-222222222222'), 'PROD-004'): [
                {"location": "D-04-01", "available": Decimal('10.0000')},
            ],
        }

        # Mock reservations storage
        self.reservations = {}  # reservation_id -> {"sku": str, "qty": Decimal, "location": str}

    def check_availability(self, sku: str, qty: Decimal, warehouse_id: UUID) -> List[Dict[str, Any]]:
        """
        Check availability using mock data.

        Returns available locations that can fulfill the requested quantity.
        """
        key = (warehouse_id, sku)
        locations = self.mock_inventory.get(key, [])

        # Filter locations that have sufficient quantity
        available_locations = [
            loc for loc in locations
            if loc["available"] >= qty
        ]

        if not available_locations:
            total_available = sum(loc["available"] for loc in locations)
            raise InventoryUnavailableException(
                sku=sku,
                requested_qty=float(qty),
                available_qty=float(total_available)
            )

        return available_locations

    def reserve(self, sku: str, qty: Decimal, location: str, reference: str) -> Dict[str, Any]:
        """
        Create a mock reservation.

        For testing purposes, always succeeds if inventory is available.
        """
        # Generate deterministic reservation ID based on inputs
        reservation_id = f"RES-{reference}-{sku}-{location}-{qty}"

        # Store reservation
        self.reservations[reservation_id] = {
            "sku": sku,
            "qty": qty,
            "location": location,
            "reference": reference
        }

        return {
            "reservation_id": reservation_id,
            "reserved_qty": qty
        }

    def release(self, reservation_id: str) -> bool:
        """
        Release a mock reservation.

        For testing purposes, always succeeds if reservation exists.
        """
        if reservation_id in self.reservations:
            del self.reservations[reservation_id]
            return True

        # For testing edge cases, you might want to raise an exception here
        # But for now, we'll assume external reservations might not be tracked
        return True


# Global adapter instance - in production, this would be configured differently
inventory_adapter = MockInventoryAdapter()


def get_inventory_adapter() -> InventoryAdapterInterface:
    """
    Factory function to get the current inventory adapter.

    In production, this could be configured to return different implementations
    based on settings (mock vs real inventory system).
    """
    return inventory_adapter


def switch_to_mock_adapter():
    """Switch to mock adapter for testing."""
    global inventory_adapter
    inventory_adapter = MockInventoryAdapter()


def switch_to_real_adapter(real_adapter: InventoryAdapterInterface):
    """
    Switch to real inventory adapter implementation.

    Args:
        real_adapter: Real implementation of InventoryAdapterInterface
    """
    global inventory_adapter
    inventory_adapter = real_adapter
