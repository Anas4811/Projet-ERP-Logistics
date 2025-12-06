"""
Shipment views for Order Fulfillment & Distribution.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Shipment
from ..services import ShippingService
from ..serializers.shipment_serializers import (
    ShipmentListSerializer, ShipmentDetailSerializer,
    ShipmentTrackingSerializer, ShipmentStatusUpdateSerializer,
    ShipmentManifestSerializer, ShipmentSummarySerializer
)
from ..permissions import IsWarehouseStaff


class ShipmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Shipment management.

    Provides CRUD operations and workflow actions for shipments.
    """

    queryset = Shipment.objects.all()
    permission_classes = [IsWarehouseStaff]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ShipmentListSerializer
        elif self.action == 'summary':
            return ShipmentSummarySerializer
        elif self.action == 'assign_tracking':
            return ShipmentTrackingSerializer
        elif self.action == 'update_status':
            return ShipmentStatusUpdateSerializer
        elif self.action == 'manifest':
            return ShipmentManifestSerializer
        else:
            return ShipmentDetailSerializer

    @action(detail=True, methods=['post'])
    def assign_tracking(self, request, pk=None):
        """Assign tracking number to a shipment."""
        shipment = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_shipment = ShippingService.assign_tracking(
                str(shipment.id), serializer.validated_data['tracking_number'], request.user
            )
            shipment_serializer = ShipmentDetailSerializer(updated_shipment)
            return Response({
                'success': True,
                'data': shipment_serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'TRACKING_ASSIGNMENT_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update shipment status."""
        shipment = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_shipment = ShippingService.update_shipment_status(
                str(shipment.id), serializer.validated_data['status'],
                serializer.validated_data, request.user
            )
            shipment_serializer = ShipmentDetailSerializer(updated_shipment)
            return Response({
                'success': True,
                'data': shipment_serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'STATUS_UPDATE_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def manifest(self, request, pk=None):
        """Generate and return shipment manifest."""
        shipment = self.get_object()

        try:
            manifest = ShippingService.generate_manifest(str(shipment.id))
            return Response({
                'success': True,
                'data': manifest
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'MANIFEST_GENERATION_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get shipment summary."""
        shipment = self.get_object()

        try:
            serializer = self.get_serializer(shipment)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'SUMMARY_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)
