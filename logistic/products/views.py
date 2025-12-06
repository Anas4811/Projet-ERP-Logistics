from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, ProductCategory
from .serializers import ProductSerializer, ProductListSerializer, ProductCategorySerializer
from users.permissions import IsAdminOrWarehouseManager, IsWorkerOrAbove


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminOrWarehouseManager()]
        return [IsWorkerOrAbove()]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "sku", "description"]
    filterset_fields = ["category", "is_active", "unit"]
    ordering_fields = ["name", "sku", "created_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        return ProductSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminOrWarehouseManager()]
        return [IsWorkerOrAbove()]

