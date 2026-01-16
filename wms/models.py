from django.db import models
from django.db.models import Q

# Create your models here.


class Warehouse(models.Model):
    name = models.CharField(max_length=200, unique=True)
    location = models.CharField(max_length=255)
    capacity = models.DecimalField(max_digits=18, decimal_places=3, default=0)

    def __str__(self) -> str:
        return self.name


class Zone(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='zones')
    name = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['warehouse', 'name'], name='uniq_zone_per_warehouse'),
        ]

    def __str__(self) -> str:
        return f"{self.warehouse} / {self.name}"


class Aisle(models.Model):
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='aisles')
    name = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['zone', 'name'], name='uniq_aisle_per_zone'),
        ]

    def __str__(self) -> str:
        return f"{self.zone} / {self.name}"


class Rack(models.Model):
    aisle = models.ForeignKey(Aisle, on_delete=models.CASCADE, related_name='racks')
    name = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['aisle', 'name'], name='uniq_rack_per_aisle'),
        ]

    def __str__(self) -> str:
        return f"{self.aisle} / {self.name}"


class Bin(models.Model):
    rack = models.ForeignKey(Rack, on_delete=models.CASCADE, related_name='bins')
    name = models.CharField(max_length=200)
    capacity = models.DecimalField(max_digits=18, decimal_places=3, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['rack', 'name'], name='uniq_bin_per_rack'),
        ]

    def __str__(self) -> str:
        return f"{self.rack} / {self.name}"

    @property
    def warehouse(self) -> Warehouse:
        return self.rack.aisle.zone.warehouse

    @property
    def zone(self) -> Zone:
        return self.rack.aisle.zone


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True)
    unit = models.CharField(max_length=50)
    default_batch_number = models.CharField(max_length=100, blank=True, null=True)
    default_expiry_date = models.DateField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['category', 'name', 'unit'], name='uniq_product_category_name_unit'),
        ]

    def __str__(self) -> str:
        return f"{self.sku} - {self.name}"


class StockItem(models.Model):
    bin = models.ForeignKey(Bin, on_delete=models.CASCADE, related_name='stock_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='stock_items')
    quantity = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    batch_number = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['bin', 'product', 'batch_number', 'serial_number', 'expiry_date'],
                name='uniq_stockitem_key',
            ),
            models.CheckConstraint(condition=Q(quantity__gte=0), name='stockitem_qty_gte_0'),
        ]

    def __str__(self) -> str:
        return f"{self.product} @ {self.bin} ({self.quantity})"


class PutawayRule(models.Model):
    priority = models.PositiveIntegerField(default=100)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True)
    product_category = models.CharField(max_length=200, blank=True, null=True)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='putaway_rules')

    class Meta:
        ordering = ['priority', 'id']

    def __str__(self) -> str:
        target = self.product.sku if self.product_id else (self.product_category or '*')
        return f"{target} -> {self.zone}"


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        RECEIPT = 'RECEIPT'
        ISSUE = 'ISSUE'
        TRANSFER = 'TRANSFER'
        ADJUSTMENT = 'ADJUSTMENT'
        PICK = 'PICK'
        PUTAWAY = 'PUTAWAY'

    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    reference = models.CharField(max_length=100, blank=True, null=True)

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements')
    quantity = models.DecimalField(max_digits=18, decimal_places=3)

    from_bin = models.ForeignKey(
        Bin,
        on_delete=models.PROTECT,
        related_name='movements_out',
        blank=True,
        null=True,
    )
    to_bin = models.ForeignKey(
        Bin,
        on_delete=models.PROTECT,
        related_name='movements_in',
        blank=True,
        null=True,
    )

    batch_number = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name='movement_qty_gt_0'),
        ]

    def __str__(self) -> str:
        return f"{self.movement_type} {self.product} ({self.quantity})"


class OutboundOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT'
        RELEASED = 'RELEASED'
        PICKED = 'PICKED'
        CLOSED = 'CLOSED'

    order_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.order_number


class OutboundOrderLine(models.Model):
    order = models.ForeignKey(OutboundOrder, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='outbound_lines')
    quantity_requested = models.DecimalField(max_digits=18, decimal_places=3)
    quantity_picked = models.DecimalField(max_digits=18, decimal_places=3, default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity_requested__gt=0), name='outbound_line_qty_req_gt_0'),
            models.CheckConstraint(condition=Q(quantity_picked__gte=0), name='outbound_line_qty_picked_gte_0'),
        ]

    def __str__(self) -> str:
        return f"{self.order} / {self.product}"


class PickConfirmation(models.Model):
    order_line = models.ForeignKey(OutboundOrderLine, on_delete=models.CASCADE, related_name='pick_confirmations')
    from_bin = models.ForeignKey(Bin, on_delete=models.PROTECT, related_name='pick_confirmations')
    to_bin = models.ForeignKey(
        Bin,
        on_delete=models.PROTECT,
        related_name='pick_confirmations_in',
        blank=True,
        null=True,
    )
    quantity = models.DecimalField(max_digits=18, decimal_places=3)
    batch_number = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name='pick_qty_gt_0'),
        ]

    def __str__(self) -> str:
        return f"PICK {self.order_line} ({self.quantity})"
