"""
Custom permissions for Order Fulfillment & Distribution module.
"""

from rest_framework.permissions import BasePermission


class IsWarehouseStaff(BasePermission):
    """
    Permission that allows access only to warehouse staff users.

    Checks if user is staff or belongs to 'warehouse_staff' group.
    This is pluggable - can be customized based on your user model setup.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Check if user is staff
        if user.is_staff:
            return True

        # Check if user belongs to warehouse_staff group
        # This assumes you have a groups system set up
        return user.groups.filter(name='warehouse_staff').exists()


class IsOrderOwnerOrWarehouseStaff(BasePermission):
    """
    Permission that allows access to order owners or warehouse staff.

    For order-related operations, allows the customer who created the order
    or warehouse staff to access/modify the order.
    """

    def has_permission(self, request, view):
        """Check if user has permission to access the view."""
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Warehouse staff can access all orders
        if IsWarehouseStaff().has_permission(request, view):
            return True

        # For list views, allow access - object permissions will filter
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Warehouse staff can access all orders
        if IsWarehouseStaff().has_permission(request, view):
            return True

        # Order owners can access their own orders
        if hasattr(obj, 'customer') and obj.customer == user:
            return True

        return False


class CanApproveOrders(BasePermission):
    """
    Permission for approving orders.

    Typically restricted to warehouse managers or supervisors.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Check for management roles
        return (
            user.is_staff or
            user.groups.filter(name__in=['warehouse_manager', 'order_supervisor']).exists()
        )
