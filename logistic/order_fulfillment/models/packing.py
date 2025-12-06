"""
Packing models for Order Fulfillment & Distribution.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class PackingTaskStatus(models.TextChoices):
    """Packing task status enumeration."""
    NOT_STARTED = 'NOT_STARTED', 'Not Started'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class PackageType(models.TextChoices):
    """Package type enumeration."""
    BOX = 'BOX', 'Box'
    PALLET = 'PALLET', 'Pallet'
    CONTAINER = 'CONTAINER', 'Container'
    ENVELOPE = 'ENVELOPE', 'Envelope'


class PackingTask(models.Model):
    """
    Packing task for grouping picked items into packages.

    Manages the packing process for orders after picking is complete.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        'Order',
        on_delete=models.CASCADE,
        related_name='packing_tasks',
        help_text="Order this packing task belongs to"
    )

    # Task identification
    task_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique packing task identifier"
    )

    # Assignment
    packer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_packing_tasks',
        help_text="Warehouse staff assigned to this packing task"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=PackingTaskStatus.choices,
        default=PackingTaskStatus.NOT_STARTED,
        help_text="Current packing task status"
    )

    # Progress tracking
    total_items = models.PositiveIntegerField(default=0)
    completed_items = models.PositiveIntegerField(default=0)

    # Timestamps
    assigned_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Packing task notes or special instructions"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['packer', 'status']),
            models.Index(fields=['order', 'status']),
        ]

    def __str__(self):
        return f"Packing Task {self.task_number} - {self.status}"

    def assign_packer(self, packer):
        """Assign a packer to this task."""
        self.packer = packer
        self.assigned_at = timezone.now()
        self.save()

    def start_packing(self):
        """Mark task as started."""
        if self.status == PackingTaskStatus.NOT_STARTED:
            self.status = PackingTaskStatus.IN_PROGRESS
            self.started_at = timezone.now()
            self.save()

    def complete_task(self):
        """Mark task as completed."""
        if self.status == PackingTaskStatus.IN_PROGRESS:
            self.status = PackingTaskStatus.COMPLETED
            self.completed_at = timezone.now()
            self.save()

    @property
    def progress_percentage(self):
        """Calculate completion percentage."""
        if self.total_items == 0:
            return 100.0
        return (self.completed_items / self.total_items) * 100.0


class Package(models.Model):
    """
    Individual package containing order items.

    Represents a physical package (box, pallet, etc.) with dimensions and contents.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    packing_task = models.ForeignKey(
        PackingTask,
        on_delete=models.CASCADE,
        related_name='packages',
        help_text="Packing task this package belongs to"
    )

    # Package identification
    package_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique package identifier"
    )

    # Package specifications
    package_type = models.CharField(
        max_length=20,
        choices=PackageType.choices,
        default=PackageType.BOX,
        help_text="Type of package"
    )

    # Dimensions (in cm)
    length = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Package length in cm"
    )
    width = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Package width in cm"
    )
    height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Package height in cm"
    )

    # Weight information
    empty_weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Weight of empty package in kg"
    )
    gross_weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total weight including contents in kg"
    )

    # Validation
    max_weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum allowed weight for this package type"
    )

    # Status
    is_sealed = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    sealed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Package notes or special handling instructions"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional package metadata"
    )

    class Meta:
        ordering = ['packing_task', 'created_at']
        indexes = [
            models.Index(fields=['packing_task', 'is_sealed']),
            models.Index(fields=['package_number']),
        ]

    def __str__(self):
        return f"Package {self.package_number} - {self.package_type}"

    def seal_package(self):
        """Mark package as sealed."""
        if not self.is_sealed:
            self.is_sealed = True
            self.sealed_at = timezone.now()
            self.save()

    @property
    def volume(self):
        """Calculate package volume in cubic cm."""
        if self.length and self.width and self.height:
            return self.length * self.width * self.height
        return None

    @property
    def net_weight(self):
        """Calculate net weight (contents only)."""
        if self.gross_weight:
            return self.gross_weight - self.empty_weight
        return None

    @property
    def is_overweight(self):
        """Check if package exceeds maximum weight."""
        if self.max_weight and self.gross_weight:
            return self.gross_weight > self.max_weight
        return False


class PackageItem(models.Model):
    """
    Through model linking packages to order items.

    Tracks which items are in which packages and quantities.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        related_name='package_items',
        help_text="Package containing this item"
    )
    order_item = models.ForeignKey(
        'OrderItem',
        on_delete=models.CASCADE,
        related_name='package_items',
        help_text="Order item in this package"
    )

    # Quantity in this package
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Quantity of this item in the package"
    )

    # Position information (for large packages)
    position_x = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="X position in package (for pallets/containers)"
    )
    position_y = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Y position in package (for pallets/containers)"
    )
    position_z = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Z position in package (for pallets/containers)"
    )

    class Meta:
        unique_together = ['package', 'order_item']
        indexes = [
            models.Index(fields=['package', 'order_item']),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.order_item.product_sku} in {self.package.package_number}"
