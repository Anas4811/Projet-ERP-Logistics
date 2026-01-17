"""
Order model for Order Fulfillment & Distribution.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class OrderStatus(models.TextChoices):
    """Order status enumeration with workflow states."""
    CREATED = 'CREATED', 'Created'
    APPROVED = 'APPROVED', 'Approved'
    ALLOCATED = 'ALLOCATED', 'Allocated'
    PICKING = 'PICKING', 'Picking'
    PACKING = 'PACKING', 'Packing'
    SHIPPED = 'SHIPPED', 'Shipped'
    DELIVERED = 'DELIVERED', 'Delivered'
    CANCELLED = 'CANCELLED', 'Cancelled'


class OrderPriority(models.TextChoices):
    """Order priority levels."""
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'


class Order(models.Model):
    """
    Main Order model representing customer orders in the fulfillment system.

    Tracks the complete lifecycle from creation to delivery, including
    allocations, picking, packing, and shipping status.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique order identifier (auto-generated)"
    )

    # Customer relationship - using AUTH_USER_MODEL as specified
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        help_text="Customer who placed the order"
    )

    # Status and priority
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.CREATED,
        help_text="Current order status in the fulfillment workflow"
    )
    priority = models.CharField(
        max_length=10,
        choices=OrderPriority.choices,
        default=OrderPriority.MEDIUM,
        help_text="Order priority level"
    )

    # Financial information
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Order subtotal before taxes/shipping"
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Tax amount"
    )
    shipping_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Shipping cost"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total order amount"
    )

    # Warehouse assignment (placeholder - integrate with Warehouse module)
    warehouse_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Assigned warehouse UUID (placeholder for Warehouse module integration)"
    )

    # Additional metadata
    notes = models.TextField(
        blank=True,
        help_text="Order notes or special instructions"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional flexible metadata (shipping preferences, etc.)"
    )

    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_orders',
        help_text="User who created the order"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_orders',
        help_text="User who last updated the order"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['order_number']),
        ]

    def __str__(self):
        return f"Order {self.order_number} - {self.customer}"

    def save(self, *args, **kwargs):
        """Override save to auto-generate order number if not provided."""
        if not self.order_number:
            # Simple order number generation - can be customized
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.order_number = f"ORD-{timestamp}-{str(self.id)[:8].upper()}"

        # Calculate total if not set
        if self.total_amount == Decimal('0.00') and (self.subtotal or self.tax_amount or self.shipping_amount):
            self.total_amount = self.subtotal + self.tax_amount + self.shipping_amount

        super().save(*args, **kwargs)

    @property
    def is_allocated(self):
        """Check if order has been allocated."""
        return self.status in [OrderStatus.ALLOCATED, OrderStatus.PICKING,
                              OrderStatus.PACKING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]

    @property
    def is_picking_started(self):
        """Check if picking has started."""
        return self.status in [OrderStatus.PICKING, OrderStatus.PACKING,
                              OrderStatus.SHIPPED, OrderStatus.DELIVERED]

    @property
    def is_packing_started(self):
        """Check if packing has started."""
        return self.status in [OrderStatus.PACKING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]

    @property
    def is_shipped(self):
        """Check if order has been shipped."""
        return self.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]

    @property
    def is_delivered(self):
        """Check if order has been delivered."""
        return self.status == OrderStatus.DELIVERED

    @property
    def can_be_cancelled(self):
        """Check if order can still be cancelled."""
        return self.status not in [OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]
