from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin


class IsAdminOrWarehouseManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_admin or request.user.is_warehouse_manager
        )


class IsWorkerOrAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

