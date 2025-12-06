"""
Order views for Order Fulfillment & Distribution.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from ..models import Order
from ..services import OrderService, AllocationService, PickingService, PackingService, ShippingService
from ..serializers.order_serializers import (
    OrderCreateSerializer, OrderUpdateSerializer, OrderListSerializer,
    OrderDetailSerializer, OrderSummarySerializer
)
from ..permissions import IsWarehouseStaff, IsOrderOwnerOrWarehouseStaff, CanApproveOrders


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Order management.

    Provides CRUD operations and workflow actions for orders.
    """

    queryset = Order.objects.all()
    permission_classes = [IsOrderOwnerOrWarehouseStaff]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return OrderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return OrderUpdateSerializer
        elif self.action == 'list':
            return OrderListSerializer
        elif self.action == 'summary':
            return OrderSummarySerializer
        else:
            return OrderDetailSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user

        # Ensure user is authenticated (should be checked by permissions, but double-check)
        if not user.is_authenticated:
            return Order.objects.none()

        # Warehouse staff can see all orders
        if IsWarehouseStaff().has_permission(self.request, self):
            return Order.objects.all()

        # Regular users can only see their own orders
        return Order.objects.filter(customer=user)

    def perform_create(self, serializer):
        """Create order using service."""
        # Creation is handled in serializer
        pass

    @action(detail=True, methods=['post'], permission_classes=[CanApproveOrders])
    def approve(self, request, pk=None):
        """Approve an order for fulfillment."""
        order = self.get_object()

        try:
            updated_order = OrderService.approve_order(str(order.id), request.user)
            serializer = self.get_serializer(updated_order)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'APPROVAL_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsWarehouseStaff])
    def allocate(self, request, pk=None):
        """Allocate inventory for an approved order."""
        order = self.get_object()

        try:
            allocation_result = AllocationService.allocate(str(order.id), request.user)
            return Response({
                'success': True,
                'data': allocation_result
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'ALLOCATION_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsWarehouseStaff])
    def generate_picking(self, request, pk=None):
        """Generate picking tasks for an allocated order."""
        order = self.get_object()

        try:
            picking_result = PickingService.generate_picking_tasks(str(order.id), request.user)
            return Response({
                'success': True,
                'data': picking_result
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'PICKING_GENERATION_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsWarehouseStaff])
    def create_packing(self, request, pk=None):
        """Create packing task for an order ready for packing."""
        order = self.get_object()

        try:
            packing_task = PackingService.create_packing_task(str(order.id), request.user)
            return Response({
                'success': True,
                'data': {
                    'task_id': packing_task.id,
                    'task_number': packing_task.task_number,
                    'status': packing_task.status
                }
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'PACKING_CREATION_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsWarehouseStaff])
    def create_shipment(self, request, pk=None):
        """Create shipment for a completed order."""
        order = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            shipment = ShippingService.create_shipment(str(order.id), serializer.validated_data, request.user)
            return Response({
                'success': True,
                'data': {
                    'shipment_id': shipment.id,
                    'shipment_number': shipment.shipment_number,
                    'carrier': shipment.carrier,
                    'status': shipment.status
                }
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'SHIPMENT_CREATION_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[CanApproveOrders])
    def cancel(self, request, pk=None):
        """Cancel an order."""
        order = self.get_object()
        reason = request.data.get('reason', '')

        try:
            cancelled_order = OrderService.cancel_order(str(order.id), request.user, reason)
            serializer = self.get_serializer(cancelled_order)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'CANCELLATION_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get comprehensive order summary."""
        order = self.get_object()

        try:
            summary = OrderService.get_order_summary(str(order.id))
            return Response({
                'success': True,
                'data': summary
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'SUMMARY_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[IsWarehouseStaff])
    def allocation_summary(self, request, pk=None):
        """Get allocation summary for an order."""
        order = self.get_object()

        try:
            summary = AllocationService.get_allocation_summary(str(order.id))
            return Response({
                'success': True,
                'data': summary
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'ALLOCATION_SUMMARY_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[IsWarehouseStaff])
    def picking_summary(self, request, pk=None):
        """Get picking summary for an order."""
        order = self.get_object()

        try:
            summary = PickingService.get_picking_summary(str(order.id))
            return Response({
                'success': True,
                'data': summary
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'PICKING_SUMMARY_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[IsWarehouseStaff])
    def packing_summary(self, request, pk=None):
        """Get packing summary for an order."""
        order = self.get_object()

        try:
            summary = PackingService.get_packing_summary(str(order.id))
            return Response({
                'success': True,
                'data': summary
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'PACKING_SUMMARY_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[IsWarehouseStaff])
    def shipping_summary(self, request, pk=None):
        """Get shipping summary for an order."""
        order = self.get_object()

        try:
            summary = ShippingService.get_shipment_summary(str(order.id))
            return Response({
                'success': True,
                'data': summary
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'SHIPPING_SUMMARY_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)
