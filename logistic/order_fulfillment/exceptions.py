"""
Custom exceptions for Order Fulfillment & Distribution module.
"""

from typing import Dict, Any


class BusinessException(Exception):
    """Base exception for business logic errors."""

    def __init__(self, message: str, code: str = "BUSINESS_ERROR", details: Dict[str, Any] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class InvalidTransitionException(BusinessException):
    """Raised when attempting an invalid workflow transition."""

    def __init__(self, current_status: str, attempted_status: str, entity_type: str = "order"):
        message = f"Invalid transition for {entity_type}: cannot move from {current_status} to {attempted_status}"
        super().__init__(message, "INVALID_TRANSITION", {
            "current_status": current_status,
            "attempted_status": attempted_status,
            "entity_type": entity_type
        })


class AllocationException(BusinessException):
    """Raised when allocation operations fail."""

    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, "ALLOCATION_ERROR", details)


class InventoryUnavailableException(BusinessException):
    """Raised when inventory is not available for allocation."""

    def __init__(self, sku: str, requested_qty: float, available_qty: float = 0.0):
        message = f"Insufficient inventory for SKU {sku}: requested {requested_qty}, available {available_qty}"
        super().__init__(message, "INVENTORY_UNAVAILABLE", {
            "sku": sku,
            "requested_quantity": requested_qty,
            "available_quantity": available_qty
        })


class ValidationException(BusinessException):
    """Raised when data validation fails."""

    def __init__(self, message: str, field_errors: Dict[str, Any] = None):
        super().__init__(message, "VALIDATION_ERROR", field_errors or {})
