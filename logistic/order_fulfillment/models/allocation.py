"""
Allocation model for inventory reservation in Order Fulfillment.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone


class AllocationStatus(models.TextChoices):
    """Allocation status enumeration."""
    RESERVED = 'RESERVED', 'Reserved'
    RELEASED = 'RELEASED', 'Released'
    CONSUMED = 'CONSUMED', 'Consumed'


class Allocation(models.Model):
    """
    Inventory allocation/reservation for order items.

    Reserves specific quantities from specific warehouse locations
    for order fulfillment.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    order = models.ForeignKey(
        'Order',
        on_delete=models.CASCADE,
        related_name='allocations',
        help_text="Order this allocation belongs to"
    )
    order_item = models.ForeignKey(
        'OrderItem',
        on_delete=models.CASCADE,
        related_name='allocations',
        help_text="Order item this allocation is for"
    )

    # Warehouse and location information
    warehouse_id = models.UUIDField(
        help_text="Warehouse UUID (placeholder for Warehouse module integration)"
    )
    location = models.CharField(
        max_length=100,
        help_text="Specific warehouse location (aisle, shelf, bin, etc.)"
    )

    # Allocation details
    quantity_reserved = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Quantity reserved at this location"
    )
    status = models.CharField(
        max_length=20,
        choices=AllocationStatus.choices,
        default=AllocationStatus.RESERVED,
        help_text="Current allocation status"
    )

    # External system reference (from InventoryAdapter)
    reservation_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="External reservation ID from inventory system"
    )

    # Metadata
    allocated_at = models.DateTimeField(default=timezone.now)
    released_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(
        blank=True,
        help_text="Allocation notes or special handling instructions"
    )

    class Meta:
        ordering = ['-allocated_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['warehouse_id', 'location']),
            models.Index(fields=['reservation_id']),
            models.Index(fields=['status', 'allocated_at']),
        ]

    def __str__(self):
        return f"Allocation {self.reservation_id} - {self.quantity_reserved} units at {self.location}"

    def release(self):
        """Mark allocation as released."""
        if self.status == AllocationStatus.RESERVED:
            self.status = AllocationStatus.RELEASED
            self.released_at = timezone.now()
            self.save()

    def consume(self):
        """Mark allocation as consumed (picked/packed)."""
        if self.status == AllocationStatus.RESERVED:
            self.status = AllocationStatus.CONSUMED
            self.consumed_at = timezone.now()
            self.save()

    @property
    def is_active(self):
        """Check if allocation is still active."""
        return self.status == AllocationStatus.RESERVED

    @property
    def can_be_released(self):
        """Check if allocation can be released."""
        return self.status == AllocationStatus.RESERVED
