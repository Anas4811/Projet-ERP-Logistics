from django.db import transaction
from django.db.models import F, Sum
from warehouse.models import StockMovement, StockItem, StorageLocation
from products.models import Product
from .stock_service import StockService


class MovementService:
    """
    Service for handling stock movements between locations.
    """

    def __init__(self):
        self.stock_service = StockService()

    @transaction.atomic
    def move_stock(self, from_location, to_location, product, quantity, user, movement_type="relocation", notes=""):
        """
        Move stock from one location to another.

        Args:
            from_location: StorageLocation instance (can be None for putaway)
            to_location: StorageLocation instance (can be None for picking)
            product: Product instance
            quantity: Quantity to move
            user: User instance
            movement_type: Type of movement (putaway, relocation, picking, adjustment)
            notes: Optional notes

        Returns:
            StockMovement instance

        Raises:
            ValueError: If insufficient stock or invalid movement
        """
        # Validate movement
        if not from_location and not to_location:
            raise ValueError("Either from_location or to_location must be provided")

        if from_location and to_location and from_location == to_location and movement_type != "adjustment":
            raise ValueError("From and to locations cannot be the same")

        # Check available stock if moving from a location (skip for adjustments at same location)
        if from_location and (movement_type != "adjustment" or from_location != to_location):
            try:
                stock_item = StockItem.objects.get(location=from_location, product=product)
                if stock_item.available_quantity < quantity:
                    raise ValueError(
                        f"Insufficient stock. Available: {stock_item.available_quantity}, Requested: {quantity}"
                    )
            except StockItem.DoesNotExist:
                raise ValueError("No stock found at source location")

        # Check capacity if moving to a location (skip for adjustments at same location)
        if to_location and (movement_type != "adjustment" or from_location != to_location):
            current_stock = (
                StockItem.objects.filter(location=to_location).aggregate(total=Sum("quantity"))["total"] or 0
            )
            if current_stock + quantity > to_location.capacity:
                raise ValueError(
                    f"Insufficient capacity at destination. Available: {to_location.capacity - current_stock}, Requested: {quantity}"
                )

        # Create movement record
        movement = StockMovement.objects.create(
            movement_type=movement_type,
            from_location=from_location,
            to_location=to_location,
            product=product,
            quantity=quantity,
            user=user,
            notes=notes,
        )

        # Update stock quantities
        if movement_type == "adjustment" and from_location == to_location:
            # For adjustments at the same location, just update quantity
            stock_item, created = StockItem.objects.get_or_create(
                location=to_location, product=product, defaults={"quantity": quantity}
            )
            if not created:
                stock_item.quantity = F("quantity") + quantity
                stock_item.save(update_fields=["quantity"])
                stock_item.refresh_from_db()
        else:
            # Normal movement between different locations
            if from_location:
                # Remove from source
                stock_item = StockItem.objects.get(location=from_location, product=product)
                stock_item.quantity = F("quantity") - quantity
                stock_item.save(update_fields=["quantity"])
                stock_item.refresh_from_db()

                # Delete if quantity becomes zero
                if stock_item.quantity <= 0:
                    stock_item.delete()

            if to_location:
                # Add to destination
                self.stock_service.update_stock(to_location, product, quantity)

        return movement

