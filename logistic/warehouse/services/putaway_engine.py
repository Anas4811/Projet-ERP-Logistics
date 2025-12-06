from django.db.models import Q, F, Sum
from products.models import Product
from warehouse.models import StorageLocation, PutawayRule, StockItem


class PutawayEngine:
    """
    Engine to determine the best storage location for incoming stock
    based on putaway rules, availability, and capacity.
    """

    def get_best_location(self, product, quantity):
        """
        Find the best location for a product based on putaway rules.

        Args:
            product: Product instance
            quantity: Quantity to be stored

        Returns:
            StorageLocation or None
        """
        # Get active putaway rules for this product's category
        rules = PutawayRule.objects.filter(
            product_category=product.category, is_active=True
        ).order_by("priority")

        if not rules.exists():
            return None

        # Try each rule in priority order
        for rule in rules:
            locations = self._get_candidate_locations(rule, product, quantity)
            if locations:
                # Return the first available location
                return locations[0]

        return None

    def _get_candidate_locations(self, rule, product, quantity):
        """
        Get candidate locations based on a putaway rule.

        Args:
            rule: PutawayRule instance
            product: Product instance
            quantity: Quantity to be stored

        Returns:
            QuerySet of StorageLocation
        """
        # Base query: active locations matching storage type
        locations = StorageLocation.objects.filter(storage_type=rule.storage_type, is_active=True)

        # Filter by allowed categories (if specified)
        if rule.product_category:
            locations = locations.filter(
                Q(allowed_categories=rule.product_category) | Q(allowed_categories__isnull=True)
            )

        # Filter locations with available capacity
        candidate_locations = []
        for location in locations.distinct():
            # Check current stock at this location
            current_stock = (
                StockItem.objects.filter(location=location).aggregate(total=Sum("quantity"))["total"] or 0
            )

            # Check if there's space for this product
            available_capacity = location.capacity - current_stock
            if available_capacity >= quantity:
                candidate_locations.append(location)

        # Sort by available capacity (ascending - prefer locations that will be filled)
        candidate_locations.sort(key=lambda loc: self._get_available_capacity(loc))

        return candidate_locations

    def _get_available_capacity(self, location):
        """Calculate available capacity at a location"""
        current_stock = (
            StockItem.objects.filter(location=location).aggregate(total=Sum("quantity"))["total"] or 0
        )
        return float(location.capacity - current_stock)

