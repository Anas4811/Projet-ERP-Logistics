from django.db import models


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_categories"
        verbose_name = "Product Category"
        verbose_name_plural = "Product Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    UNIT_CHOICES = [
        ("piece", "Piece"),
        ("kg", "Kilogram"),
        ("g", "Gram"),
        ("l", "Liter"),
        ("ml", "Milliliter"),
        ("box", "Box"),
        ("pallet", "Pallet"),
    ]

    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name="products")
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default="piece")
    description = models.TextField(blank=True)
    weight = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Weight in kg"
    )
    dimensions = models.CharField(max_length=100, blank=True, help_text="LxWxH in cm")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

