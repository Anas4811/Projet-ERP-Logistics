"""
Shipment models for Order Fulfillment & Distribution.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class ShipmentStatus(models.TextChoices):
    """Shipment status enumeration following delivery lifecycle."""
    CREATED = 'CREATED', 'Created'
    LOADED = 'LOADED', 'Loaded'
    DISPATCHED = 'DISPATCHED', 'Dispatched'
    IN_TRANSIT = 'IN_TRANSIT', 'In Transit'
    OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY', 'Out for Delivery'
    DELIVERED = 'DELIVERED', 'Delivered'
    CANCELLED = 'CANCELLED', 'Cancelled'
    RETURNED = 'RETURNED', 'Returned'


class Shipment(models.Model):
    """
    Shipment representing one or more packages being transported together.

    Groups packages for shipping and tracks delivery status.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        'Order',
        on_delete=models.CASCADE,
        related_name='shipments',
        help_text="Order this shipment belongs to"
    )

    # Shipment identification
    shipment_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique shipment identifier"
    )

    # Shipping details
    carrier = models.CharField(
        max_length=100,
        help_text="Shipping carrier (FedEx, UPS, DHL, etc.)"
    )
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Carrier tracking number"
    )

    # Status and progress
    status = models.CharField(
        max_length=20,
        choices=ShipmentStatus.choices,
        default=ShipmentStatus.CREATED,
        help_text="Current shipment status"
    )

    # Cost information
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Cost of shipping this shipment"
    )
    insurance_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Insurance cost"
    )

    # Weight and dimensions (aggregated from packages)
    total_weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total shipment weight in kg"
    )
    total_volume = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total shipment volume in cubic cm"
    )

    # Addresses
    ship_from_address = models.JSONField(
        help_text="Origin address information"
    )
    ship_to_address = models.JSONField(
        help_text="Destination address information"
    )

    # Manifest and documentation
    manifest = models.JSONField(
        default=dict,
        blank=True,
        help_text="Shipment manifest with package details and contents"
    )

    # Assignment
    dispatcher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispatched_shipments',
        help_text="User who dispatched the shipment"
    )

    # Delivery information
    estimated_delivery_date = models.DateTimeField(null=True, blank=True)
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    delivered_by = models.CharField(
        max_length=100,
        blank=True,
        help_text="Person/name who delivered the shipment"
    )
    recipient_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Person who received the shipment"
    )

    # Timestamps
    dispatched_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Shipment notes or special delivery instructions"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional shipment metadata"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'estimated_delivery_date']),
            models.Index(fields=['carrier', 'tracking_number']),
            models.Index(fields=['order', 'status']),
            models.Index(fields=['dispatched_at']),
        ]

    def __str__(self):
        return f"Shipment {self.shipment_number} - {self.carrier} ({self.status})"

    def dispatch_shipment(self, tracking_number: str = None):
        """Mark shipment as dispatched."""
        if self.status == ShipmentStatus.CREATED or self.status == ShipmentStatus.LOADED:
            self.status = ShipmentStatus.DISPATCHED
            self.dispatched_at = timezone.now()
            if tracking_number:
                self.tracking_number = tracking_number
            self.save()

    def mark_delivered(self, recipient_name: str = None, delivered_by: str = None):
        """Mark shipment as delivered."""
        if self.status in [ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.IN_TRANSIT]:
            self.status = ShipmentStatus.DELIVERED
            self.delivered_at = timezone.now()
            self.actual_delivery_date = self.delivered_at
            if recipient_name:
                self.recipient_name = recipient_name
            if delivered_by:
                self.delivered_by = delivered_by
            self.save()

    def cancel_shipment(self):
        """Cancel the shipment."""
        if self.status not in [ShipmentStatus.DELIVERED, ShipmentStatus.CANCELLED]:
            self.status = ShipmentStatus.CANCELLED
            self.save()

    @property
    def is_delivered(self):
        """Check if shipment has been delivered."""
        return self.status == ShipmentStatus.DELIVERED

    @property
    def is_in_transit(self):
        """Check if shipment is in transit."""
        return self.status in [ShipmentStatus.IN_TRANSIT, ShipmentStatus.OUT_FOR_DELIVERY]

    @property
    def delivery_delay_days(self):
        """Calculate delivery delay in days."""
        if self.actual_delivery_date and self.estimated_delivery_date:
            delay = self.actual_delivery_date - self.estimated_delivery_date
            return delay.days
        return None


class ShipmentItem(models.Model):
    """
    Through model linking shipments to packages.

    Tracks which packages are in which shipments.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name='shipment_items',
        help_text="Shipment containing this package"
    )
    package = models.ForeignKey(
        'Package',
        on_delete=models.CASCADE,
        related_name='shipment_items',
        help_text="Package in this shipment"
    )

    # Sequence information
    sequence_number = models.PositiveIntegerField(
        help_text="Sequence number of package in shipment"
    )

    class Meta:
        ordering = ['shipment', 'sequence_number']
        unique_together = ['shipment', 'package']
        indexes = [
            models.Index(fields=['shipment', 'sequence_number']),
        ]

    def __str__(self):
        return f"Package {self.package.package_number} in Shipment {self.shipment.shipment_number}"
