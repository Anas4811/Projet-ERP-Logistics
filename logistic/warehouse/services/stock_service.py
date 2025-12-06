from django.db import transaction
from django.db.models import F
from warehouse.models import StockItem, StorageLocation
from products.models import Product


class StockService:
    """
    Service for managing stock quantities and inventory operations.
    """

    @transaction.atomic
    def update_stock(self, location, product, quantity, reserved_quantity=0):
        """
        Update stock quantity at a location.
        Creates StockItem if it doesn't exist, updates if it does.

        Args:
            location: StorageLocation instance
            product: Product instance
            quantity: Quantity to set/add
            reserved_quantity: Reserved quantity (default 0)

        Returns:
            StockItem instance
        """
        stock_item, created = StockItem.objects.get_or_create(
            location=location, product=product, defaults={"quantity": quantity, "reserved_quantity": reserved_quantity}
        )

        if not created:
            stock_item.quantity = F("quantity") + quantity
            stock_item.save(update_fields=["quantity"])
            stock_item.refresh_from_db()

        return stock_item

    @transaction.atomic
    def adjust_stock(self, location, product, quantity_delta):
        """
        Adjust stock quantity by a delta amount.

        Args:
            location: StorageLocation instance
            product: Product instance
            quantity_delta: Amount to add (positive) or subtract (negative)

        Returns:
            StockItem instance
        """
        stock_item, created = StockItem.objects.get_or_create(
            location=location, product=product, defaults={"quantity": quantity_delta}
        )

        if not created:
            stock_item.quantity = F("quantity") + quantity_delta
            stock_item.save(update_fields=["quantity"])
            stock_item.refresh_from_db()

        return stock_item

    @transaction.atomic
    def reserve_stock(self, location, product, quantity):
        """
        Reserve stock quantity.

        Args:
            location: StorageLocation instance
            product: Product instance
            quantity: Quantity to reserve

        Returns:
            StockItem instance or None if insufficient stock
        """
        try:
            stock_item = StockItem.objects.get(location=location, product=product)
            if stock_item.available_quantity >= quantity:
                stock_item.reserved_quantity = F("reserved_quantity") + quantity
                stock_item.save(update_fields=["reserved_quantity"])
                stock_item.refresh_from_db()
                return stock_item
            return None
        except StockItem.DoesNotExist:
            return None

    @transaction.atomic
    def release_reservation(self, location, product, quantity):
        """
        Release reserved stock quantity.

        Args:
            location: StorageLocation instance
            product: Product instance
            quantity: Quantity to release

        Returns:
            StockItem instance
        """
        stock_item = StockItem.objects.get(location=location, product=product)
        stock_item.reserved_quantity = F("reserved_quantity") - quantity
        stock_item.save(update_fields=["reserved_quantity"])
        stock_item.refresh_from_db()
        return stock_item

    def get_stock_by_product(self, product):
        """
        Get all stock items for a product across all locations.

        Args:
            product: Product instance

        Returns:
            QuerySet of StockItem
        """
        return StockItem.objects.filter(product=product).select_related("location")

    def get_stock_by_location(self, location):
        """
        Get all stock items at a location.

        Args:
            location: StorageLocation instance

        Returns:
            QuerySet of StockItem
        """
        return StockItem.objects.filter(location=location).select_related("product")

