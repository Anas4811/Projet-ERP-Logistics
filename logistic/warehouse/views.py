from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, F
from django.db import transaction
from .models import StorageLocation, PutawayRule, StockItem, StockMovement
from .serializers import (
    StorageLocationSerializer,
    PutawayRuleSerializer,
    StockItemSerializer,
    StockMovementSerializer,
    StockMovementCreateSerializer,
)
from warehouse.services.putaway_engine import PutawayEngine
from warehouse.services.movement_service import MovementService
from users.permissions import IsAdmin, IsAdminOrWarehouseManager, IsWorkerOrAbove


class StorageLocationViewSet(viewsets.ModelViewSet):
    queryset = StorageLocation.objects.select_related("parent").prefetch_related("allowed_categories").all()
    serializer_class = StorageLocationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "name", "notes"]
    filterset_fields = ["level", "storage_type", "is_active", "parent"]
    ordering_fields = ["code", "name", "created_at"]
    ordering = ["code"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminOrWarehouseManager()]
        return [IsWorkerOrAbove()]

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Get locations in tree structure"""
        locations = StorageLocation.objects.filter(parent__isnull=True).select_related("parent")
        serializer = self.get_serializer(locations, many=True)
        return Response(serializer.data)


class PutawayRuleViewSet(viewsets.ModelViewSet):
    queryset = PutawayRule.objects.select_related("product_category").all()
    serializer_class = PutawayRuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    filterset_fields = ["product_category", "storage_type", "is_active", "priority"]
    ordering_fields = ["priority", "name", "created_at"]
    ordering = ["priority", "name"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminOrWarehouseManager()]
        return [IsWorkerOrAbove()]

    @action(detail=False, methods=["post"])
    def get_best_location(self, request):
        """Get best location for a product based on putaway rules"""
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity", 1)

        if not product_id:
            return Response({"error": "product_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from products.models import Product

            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        engine = PutawayEngine()
        best_location = engine.get_best_location(product, quantity)

        if best_location:
            serializer = StorageLocationSerializer(best_location)
            return Response(serializer.data)
        return Response({"error": "No suitable location found"}, status=status.HTTP_404_NOT_FOUND)


class StockItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockItem.objects.select_related("location", "product").all()
    serializer_class = StockItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["product__name", "product__sku", "location__code", "location__name"]
    filterset_fields = ["location", "product"]
    ordering_fields = ["product__name", "location__code", "quantity", "last_movement_date"]
    ordering = ["-last_movement_date"]

    @action(detail=False, methods=["get"])
    def by_product(self, request):
        """Get all stock for a specific product"""
        product_id = request.query_params.get("product_id")
        if not product_id:
            return Response(
                {"error": "product_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        stock_items = self.queryset.filter(product_id=product_id)
        serializer = self.get_serializer(stock_items, many=True)

        total_quantity = stock_items.aggregate(total=Sum("quantity"))["total"] or 0
        total_reserved = stock_items.aggregate(total=Sum("reserved_quantity"))["total"] or 0

        return Response(
            {
                "stock_items": serializer.data,
                "total_quantity": total_quantity,
                "total_reserved": total_reserved,
                "total_available": total_quantity - total_reserved,
            }
        )

    @action(detail=False, methods=["get"])
    def by_location(self, request):
        """Get all stock at a specific location"""
        location_id = request.query_params.get("location_id")
        if not location_id:
            return Response(
                {"error": "location_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        stock_items = self.queryset.filter(location_id=location_id)
        serializer = self.get_serializer(stock_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        """Get low stock alerts"""
        threshold = float(request.query_params.get("threshold", 10))
        stock_items = self.queryset.filter(quantity__lte=threshold)
        serializer = self.get_serializer(stock_items, many=True)
        return Response(serializer.data)


class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.select_related("from_location", "to_location", "product", "user").all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["product__name", "product__sku", "notes"]
    filterset_fields = ["movement_type", "product", "from_location", "to_location", "user"]
    ordering_fields = ["created_at", "quantity"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return StockMovementCreateSerializer
        return StockMovementSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsWorkerOrAbove()]
        return [IsWorkerOrAbove()]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            movement_service = MovementService()
            movement = movement_service.move_stock(
                from_location=serializer.validated_data.get("from_location"),
                to_location=serializer.validated_data.get("to_location"),
                product=serializer.validated_data["product"],
                quantity=serializer.validated_data["quantity"],
                user=request.user,
                movement_type=serializer.validated_data.get("movement_type", "relocation"),
                notes=serializer.validated_data.get("notes", ""),
            )

            result_serializer = StockMovementSerializer(movement)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

