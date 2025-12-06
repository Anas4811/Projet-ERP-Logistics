"""
Workflow service for Order Fulfillment & Distribution.

Manages allowed state transitions and enforces business rules.
"""

from ..exceptions import InvalidTransitionException
from ..models import (
    Order, OrderStatus, PickingTask, PickingTaskStatus,
    PackingTask, PackingTaskStatus, Shipment, ShipmentStatus
)


class OrderWorkflow:
    """Workflow rules for Order state transitions."""

    # Define allowed transitions
    ALLOWED_TRANSITIONS = {
        OrderStatus.CREATED: [OrderStatus.APPROVED, OrderStatus.CANCELLED],
        OrderStatus.APPROVED: [OrderStatus.ALLOCATED, OrderStatus.CANCELLED],
        OrderStatus.ALLOCATED: [OrderStatus.PICKING, OrderStatus.CANCELLED],
        OrderStatus.PICKING: [OrderStatus.PACKING, OrderStatus.CANCELLED],
        OrderStatus.PACKING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
        OrderStatus.SHIPPED: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
        OrderStatus.DELIVERED: [],  # Final state
        OrderStatus.CANCELLED: [],  # Final state
    }

    @classmethod
    def validate_transition(cls, order: Order, new_status: str) -> None:
        """
        Validate if a status transition is allowed.

        Args:
            order: Order instance
            new_status: New status to transition to

        Raises:
            InvalidTransitionException: If transition is not allowed
        """
        current_status = order.status

        if current_status == new_status:
            return  # Allow no-op transitions

        allowed_transitions = cls.ALLOWED_TRANSITIONS.get(current_status, [])

        if new_status not in allowed_transitions:
            raise InvalidTransitionException(
                current_status=current_status,
                attempted_status=new_status,
                entity_type="Order"
            )

    @classmethod
    def can_transition_to(cls, order: Order, new_status: str) -> bool:
        """
        Check if transition is allowed without raising exception.

        Args:
            order: Order instance
            new_status: New status to transition to

        Returns:
            True if transition is allowed
        """
        try:
            cls.validate_transition(order, new_status)
            return True
        except InvalidTransitionException:
            return False


class PickingTaskWorkflow:
    """Workflow rules for PickingTask state transitions."""

    ALLOWED_TRANSITIONS = {
        PickingTaskStatus.NOT_STARTED: [PickingTaskStatus.IN_PROGRESS, PickingTaskStatus.CANCELLED],
        PickingTaskStatus.IN_PROGRESS: [PickingTaskStatus.COMPLETED, PickingTaskStatus.CANCELLED],
        PickingTaskStatus.COMPLETED: [],  # Final state
        PickingTaskStatus.CANCELLED: [],  # Final state
    }

    @classmethod
    def validate_transition(cls, task: PickingTask, new_status: str) -> None:
        """
        Validate if a status transition is allowed.

        Args:
            task: PickingTask instance
            new_status: New status to transition to

        Raises:
            InvalidTransitionException: If transition is not allowed
        """
        current_status = task.status

        if current_status == new_status:
            return  # Allow no-op transitions

        allowed_transitions = cls.ALLOWED_TRANSITIONS.get(current_status, [])

        if new_status not in allowed_transitions:
            raise InvalidTransitionException(
                current_status=current_status,
                attempted_status=new_status,
                entity_type="PickingTask"
            )


class PackingTaskWorkflow:
    """Workflow rules for PackingTask state transitions."""

    ALLOWED_TRANSITIONS = {
        PackingTaskStatus.NOT_STARTED: [PackingTaskStatus.IN_PROGRESS, PackingTaskStatus.CANCELLED],
        PackingTaskStatus.IN_PROGRESS: [PackingTaskStatus.COMPLETED, PackingTaskStatus.CANCELLED],
        PackingTaskStatus.COMPLETED: [],  # Final state
        PackingTaskStatus.CANCELLED: [],  # Final state
    }

    @classmethod
    def validate_transition(cls, task: PackingTask, new_status: str) -> None:
        """
        Validate if a status transition is allowed.

        Args:
            task: PackingTask instance
            new_status: New status to transition to

        Raises:
            InvalidTransitionException: If transition is not allowed
        """
        current_status = task.status

        if current_status == new_status:
            return  # Allow no-op transitions

        allowed_transitions = cls.ALLOWED_TRANSITIONS.get(current_status, [])

        if new_status not in allowed_transitions:
            raise InvalidTransitionException(
                current_status=current_status,
                attempted_status=new_status,
                entity_type="PackingTask"
            )


class ShipmentWorkflow:
    """Workflow rules for Shipment state transitions."""

    ALLOWED_TRANSITIONS = {
        ShipmentStatus.CREATED: [ShipmentStatus.LOADED, ShipmentStatus.CANCELLED],
        ShipmentStatus.LOADED: [ShipmentStatus.DISPATCHED, ShipmentStatus.CANCELLED],
        ShipmentStatus.DISPATCHED: [ShipmentStatus.IN_TRANSIT, ShipmentStatus.CANCELLED],
        ShipmentStatus.IN_TRANSIT: [ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.CANCELLED],
        ShipmentStatus.OUT_FOR_DELIVERY: [ShipmentStatus.DELIVERED, ShipmentStatus.RETURNED],
        ShipmentStatus.DELIVERED: [],  # Final state
        ShipmentStatus.CANCELLED: [],  # Final state
        ShipmentStatus.RETURNED: [],   # Final state
    }

    @classmethod
    def validate_transition(cls, shipment: Shipment, new_status: str) -> None:
        """
        Validate if a status transition is allowed.

        Args:
            shipment: Shipment instance
            new_status: New status to transition to

        Raises:
            InvalidTransitionException: If transition is not allowed
        """
        current_status = shipment.status

        if current_status == new_status:
            return  # Allow no-op transitions

        allowed_transitions = cls.ALLOWED_TRANSITIONS.get(current_status, [])

        if new_status not in allowed_transitions:
            raise InvalidTransitionException(
                current_status=current_status,
                attempted_status=new_status,
                entity_type="Shipment"
            )


def validate_order_workflow(order: Order, new_status: str) -> None:
    """
    Validate order workflow transition.

    Args:
        order: Order instance
        new_status: New status to transition to

    Raises:
        InvalidTransitionException: If transition is not allowed
    """
    OrderWorkflow.validate_transition(order, new_status)


def validate_picking_workflow(task: PickingTask, new_status: str) -> None:
    """
    Validate picking task workflow transition.

    Args:
        task: PickingTask instance
        new_status: New status to transition to

    Raises:
        InvalidTransitionException: If transition is not allowed
    """
    PickingTaskWorkflow.validate_transition(task, new_status)


def validate_packing_workflow(task: PackingTask, new_status: str) -> None:
    """
    Validate packing task workflow transition.

    Args:
        task: PackingTask instance
        new_status: New status to transition to

    Raises:
        InvalidTransitionException: If transition is not allowed
    """
    PackingTaskWorkflow.validate_transition(task, new_status)


def validate_shipment_workflow(shipment: Shipment, new_status: str) -> None:
    """
    Validate shipment workflow transition.

    Args:
        shipment: Shipment instance
        new_status: New status to transition to

    Raises:
        InvalidTransitionException: If transition is not allowed
    """
    ShipmentWorkflow.validate_transition(shipment, new_status)
