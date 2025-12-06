"""
Picking models for Order Fulfillment & Distribution.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class PickingTaskStatus(models.TextChoices):
    """Picking task status enumeration."""
    NOT_STARTED = 'NOT_STARTED', 'Not Started'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class PickingTask(models.Model):
    """
    Picking task representing a group of items to be picked together.

    Tasks are grouped by warehouse, zone, or product type for efficiency.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        'Order',
        on_delete=models.CASCADE,
        related_name='picking_tasks',
        help_text="Order this picking task belongs to"
    )

    # Task identification
    task_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique picking task identifier"
    )

    # Assignment
    picker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_picking_tasks',
        help_text="Warehouse staff assigned to this picking task"
    )

    # Status and progress
    status = models.CharField(
        max_length=20,
        choices=PickingTaskStatus.choices,
        default=PickingTaskStatus.NOT_STARTED,
        help_text="Current picking task status"
    )

    # Grouping criteria
    warehouse_id = models.UUIDField(
        help_text="Warehouse UUID where picking occurs"
    )
    zone = models.CharField(
        max_length=50,
        blank=True,
        help_text="Warehouse zone for this task"
    )
    priority = models.CharField(
        max_length=10,
        choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('URGENT', 'Urgent')],
        default='MEDIUM',
        help_text="Task priority"
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
        help_text="Picking task notes or special instructions"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['picker', 'status']),
            models.Index(fields=['order', 'status']),
            models.Index(fields=['warehouse_id', 'zone']),
        ]

    def __str__(self):
        return f"Picking Task {self.task_number} - {self.status}"

    def assign_picker(self, picker):
        """Assign a picker to this task."""
        self.picker = picker
        self.assigned_at = timezone.now()
        self.save()

    def start_picking(self):
        """Mark task as started."""
        if self.status == PickingTaskStatus.NOT_STARTED:
            self.status = PickingTaskStatus.IN_PROGRESS
            self.started_at = timezone.now()
            self.save()

    def complete_task(self):
        """Mark task as completed."""
        if self.status == PickingTaskStatus.IN_PROGRESS:
            self.status = PickingTaskStatus.COMPLETED
            self.completed_at = timezone.now()
            self.save()

    @property
    def progress_percentage(self):
        """Calculate completion percentage."""
        if self.total_items == 0:
            return 100.0
        return (self.completed_items / self.total_items) * 100.0

    @property
    def is_overdue(self):
        """Check if task is overdue (placeholder - implement based on business rules)."""
        # This could be implemented based on SLA or expected completion time
        return False


class PickingItem(models.Model):
    """
    Individual item within a picking task.

    Tracks picking progress for each order item.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    picking_task = models.ForeignKey(
        PickingTask,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Picking task this item belongs to"
    )
    order_item = models.ForeignKey(
        'OrderItem',
        on_delete=models.CASCADE,
        related_name='picking_items',
        help_text="Order item being picked"
    )

    # Picking details
    quantity_to_pick = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Quantity that should be picked"
    )
    quantity_picked = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Quantity actually picked"
    )

    # Location information
    location = models.CharField(
        max_length=100,
        help_text="Warehouse location where item should be picked from"
    )

    # Status
    is_completed = models.BooleanField(default=False)

    # Timestamps
    picked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['picking_task', 'location']
        indexes = [
            models.Index(fields=['picking_task', 'is_completed']),
            models.Index(fields=['order_item']),
        ]
        unique_together = ['picking_task', 'order_item']

    def __str__(self):
        return f"Picking {self.quantity_picked}/{self.quantity_to_pick} of {self.order_item.product_sku}"

    def update_picked_quantity(self, quantity: Decimal):
        """Update the picked quantity."""
        self.quantity_picked = quantity
        self.updated_at = timezone.now()

        if self.quantity_picked >= self.quantity_to_pick:
            self.is_completed = True
            self.picked_at = timezone.now()

        self.save()

    @property
    def remaining_to_pick(self):
        """Quantity still needing to be picked."""
        return self.quantity_to_pick - self.quantity_picked

    @property
    def is_fully_picked(self):
        """Check if item is fully picked."""
        return self.quantity_picked >= self.quantity_to_pick
