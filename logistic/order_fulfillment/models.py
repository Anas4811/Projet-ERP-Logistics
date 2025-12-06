# Order Fulfillment & Distribution Models
# All models are defined in this file to ensure Django can discover them properly

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

    # Warehouse assignment (placeholder for Warehouse module integration)
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


class OrderItem(models.Model):
    """
    Individual items within an order.

    Tracks quantities at different stages of the fulfillment process.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
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
        Order,
        on_delete=models.CASCADE,
        related_name='allocations',
        help_text="Order this allocation belongs to"
    )
    order_item = models.ForeignKey(
        OrderItem,
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
        Order,
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
        OrderItem,
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
        Order,
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
        OrderItem,
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
        Order,
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
        Package,
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


class AuditLog(models.Model):
    """
    Generic audit log for tracking changes to orders, tasks, and shipments.

    Provides comprehensive audit trail for compliance and debugging.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Entity being audited
    entity_type = models.CharField(
        max_length=50,
        help_text="Type of entity (Order, PickingTask, Shipment, etc.)"
    )
    entity_id = models.UUIDField(
        help_text="UUID of the entity being audited"
    )

    # Action performed
    action = models.CharField(
        max_length=50,
        help_text="Action performed (created, updated, status_changed, etc.)"
    )

    # User who performed the action
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        help_text="User who performed the action"
    )

    # Before and after states
    old_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="Previous values before the change"
    )
    new_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="New values after the change"
    )

    # Change details
    field_changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Specific fields that were changed"
    )

    # Context information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Metadata
    timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the change"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional audit metadata"
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.entity_type} {self.entity_id} - {self.action} by {self.user} at {self.timestamp}"

    @classmethod
    def log_change(cls, entity, action: str, user=None, old_values=None,
                   new_values=None, field_changes=None, notes="", metadata=None):
        """
        Create an audit log entry for an entity change.

        Args:
            entity: The model instance being audited
            action: The action performed
            user: User who performed the action
            old_values: Previous state
            new_values: New state
            field_changes: Specific field changes
            notes: Additional notes
            metadata: Additional metadata
        """
        return cls.objects.create(
            entity_type=entity.__class__.__name__,
            entity_id=entity.id,
            action=action,
            user=user,
            old_values=old_values or {},
            new_values=new_values or {},
            field_changes=field_changes or {},
            notes=notes,
            metadata=metadata or {}
        )

    @classmethod
    def log_status_change(cls, entity, old_status: str, new_status: str, user=None, notes=""):
        """
        Log a status change for an entity.

        Args:
            entity: The model instance
            old_status: Previous status
            new_status: New status
            user: User making the change
            notes: Additional notes
        """
        return cls.log_change(
            entity=entity,
            action='status_changed',
            user=user,
            old_values={'status': old_status},
            new_values={'status': new_status},
            field_changes={'status': {'old': old_status, 'new': new_status}},
            notes=notes
        )
