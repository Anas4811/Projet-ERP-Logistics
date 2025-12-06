"""
OrderItem model for Order Fulfillment & Distribution.
"""

import uuid
from decimal import Decimal
from django.db import models


class OrderItem(models.Model):
    """
    Individual items within an order.

    Tracks quantities at different stages of the fulfillment process.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        'Order',
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Order this item belongs to"
    )

    # Product information (placeholders for Product module integration)
    product_id = models.UUIDField(
        help_text="Product UUID (placeholder for Product module integration)"
    )
    product_sku = models.CharField(
        max_length=100,
        help_text="Product SKU for inventory tracking"
    )
    product_name = models.CharField(
        max_length=255,
        help_text="Product name at time of order"
    )

    # Quantities tracking fulfillment stages
    quantity_ordered = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Original quantity ordered by customer"
    )
    quantity_allocated = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Quantity allocated/reserved in inventory"
    )
    quantity_picked = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Quantity picked from warehouse"
    )
    quantity_packed = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Quantity packed into packages"
    )
    quantity_shipped = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Quantity shipped"
    )

    # Pricing and weight information
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Price per unit"
    )
    unit_weight = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Weight per unit (kg)"
    )

    # Calculated fields
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total price for this line item (quantity_ordered * unit_price)"
    )
    total_weight = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Total weight for this line item"
    )

    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional item-specific metadata"
    )

    class Meta:
        ordering = ['order', 'product_sku']
        indexes = [
            models.Index(fields=['order', 'product_sku']),
            models.Index(fields=['quantity_allocated', 'quantity_picked']),
        ]
        unique_together = ['order', 'product_id']

    def __str__(self):
        return f"{self.product_sku} - {self.quantity_ordered} units"

    def save(self, *args, **kwargs):
        """Override save to calculate derived fields."""
        # Calculate line total
        self.line_total = self.quantity_ordered * self.unit_price

        # Calculate total weight if unit weight is provided
        if self.unit_weight is not None:
            self.total_weight = self.quantity_ordered * self.unit_weight

        super().save(*args, **kwargs)

    @property
    def remaining_to_allocate(self):
        """Quantity still needing allocation."""
        return self.quantity_ordered - self.quantity_allocated

    @property
    def remaining_to_pick(self):
        """Quantity still needing to be picked."""
        return self.quantity_allocated - self.quantity_picked

    @property
    def remaining_to_pack(self):
        """Quantity still needing to be packed."""
        return self.quantity_picked - self.quantity_packed

    @property
    def remaining_to_ship(self):
        """Quantity still needing to be shipped."""
        return self.quantity_packed - self.quantity_shipped

    @property
    def is_fully_allocated(self):
        """Check if item is fully allocated."""
        return self.quantity_allocated >= self.quantity_ordered

    @property
    def is_fully_picked(self):
        """Check if item is fully picked."""
        return self.quantity_picked >= self.quantity_allocated

    @property
    def is_fully_packed(self):
        """Check if item is fully packed."""
        return self.quantity_packed >= self.quantity_picked

    @property
    def is_fully_shipped(self):
        """Check if item is fully shipped."""
        return self.quantity_shipped >= self.quantity_packed
