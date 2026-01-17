from django.db import models
from django.core.validators import MinValueValidator
from products.models import Product, ProductCategory


class StorageLocation(models.Model):
    STORAGE_TYPE_CHOICES = [
        ("pallet", "Pallet"),
        ("box", "Box"),
        ("bulk", "Bulk"),
    ]

    LOCATION_LEVEL_CHOICES = [
        ("zone", "Zone"),
        ("aisle", "Aisle"),
        ("rack", "Rack"),
        ("level", "Level"),
        ("bin", "Bin"),
    ]

    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    level = models.CharField(max_length=20, choices=LOCATION_LEVEL_CHOICES)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    storage_type = models.CharField(max_length=20, choices=STORAGE_TYPE_CHOICES)
    capacity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    capacity_unit = models.CharField(max_length=20, default="piece")
    allowed_categories = models.ManyToManyField(ProductCategory, blank=True, related_name="allowed_locations")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "storage_locations"
        verbose_name = "Storage Location"
        verbose_name_plural = "Storage Locations"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["level"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_full_path(self):
        """Returns the full hierarchical path of the location"""
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return " > ".join(path)


class PutawayRule(models.Model):
    PRIORITY_CHOICES = [
        (1, "Highest"),
        (2, "High"),
        (3, "Medium"),
        (4, "Low"),
        (5, "Lowest"),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name="putaway_rules")
    storage_type = models.CharField(max_length=20, choices=StorageLocation.STORAGE_TYPE_CHOICES)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=3)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "putaway_rules"
        verbose_name = "Putaway Rule"
        verbose_name_plural = "Putaway Rules"
        ordering = ["priority", "name"]
        indexes = [
            models.Index(fields=["product_category", "storage_type", "is_active"]),
            models.Index(fields=["priority"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.product_category.name} ({self.get_storage_type_display()})"


class StockItem(models.Model):
    location = models.ForeignKey(StorageLocation, on_delete=models.CASCADE, related_name="stock_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_items")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    reserved_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    last_movement_date = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock_items"
        verbose_name = "Stock Item"
        verbose_name_plural = "Stock Items"
        unique_together = [["location", "product"]]
        indexes = [
            models.Index(fields=["location", "product"]),
            models.Index(fields=["product"]),
            models.Index(fields=["location"]),
        ]

    def __str__(self):
        return f"{self.product.name} at {self.location.code} - {self.quantity}"

    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity


class StockMovement(models.Model):
    MOVEMENT_TYPE_CHOICES = [
        ("putaway", "Putaway"),
        ("relocation", "Relocation"),
        ("picking", "Picking"),
        ("adjustment", "Adjustment"),
    ]

    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    from_location = models.ForeignKey(
        StorageLocation, on_delete=models.PROTECT, related_name="movements_from", null=True, blank=True
    )
    to_location = models.ForeignKey(
        StorageLocation, on_delete=models.PROTECT, related_name="movements_to", null=True, blank=True
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    user = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="movements")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stock_movements"
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["product"]),
            models.Index(fields=["from_location"]),
            models.Index(fields=["to_location"]),
            models.Index(fields=["user"]),
            models.Index(fields=["movement_type"]),
        ]

    def __str__(self):
        return f"{self.movement_type} - {self.product.name} - {self.quantity} at {self.created_at}"

