"""
Packing views for Order Fulfillment & Distribution.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import PackingTask, Package
from ..services import PackingService
from ..serializers.packing_serializers import (
    PackingTaskListSerializer, PackingTaskDetailSerializer,
    PackageCreateSerializer, PackageSerializer,
    PackageItemAddSerializer, PackingTaskSummarySerializer
)
from ..permissions import IsWarehouseStaff


class PackingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Packing Task management.

    Provides CRUD operations and workflow actions for packing tasks.
    """

    queryset = PackingTask.objects.all()
    permission_classes = [IsWarehouseStaff]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return PackingTaskListSerializer
        elif self.action == 'summary':
            return PackingTaskSummarySerializer
        else:
            return PackingTaskDetailSerializer

    @action(detail=True, methods=['post'])
    def create_package(self, request, pk=None):
        """Create a new package for a packing task."""
        task = self.get_object()
        serializer = PackageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            package = PackingService.create_package(str(task.id), serializer.validated_data, request.user)
            package_serializer = PackageSerializer(package)
            return Response({
                'success': True,
                'data': package_serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'PACKAGE_CREATION_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """Add an item to a package."""
        task = self.get_object()
        serializer = PackageItemAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Find the package in this task
            package = Package.objects.get(
                packing_task=task,
                id=request.data.get('package_id')
            )

            package_item = PackingService.add_item_to_package(
                str(package.id),
                serializer.validated_data['order_item_id'],
                serializer.validated_data['quantity'],
                request.user
            )

            return Response({
                'success': True,
                'data': {
                    'package_item_id': package_item.id,
                    'quantity': package_item.quantity
                }
            })
        except Package.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'PACKAGE_NOT_FOUND',
                    'message': 'Package not found in this packing task'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'ITEM_ADDITION_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def finalize_package(self, request, pk=None):
        """Finalize and seal a package."""
        task = self.get_object()
        package_id = request.data.get('package_id')

        if not package_id:
            return Response({
                'success': False,
                'error': {
                    'code': 'MISSING_PACKAGE_ID',
                    'message': 'package_id is required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find the package in this task
            package = Package.objects.get(
                packing_task=task,
                id=package_id
            )

            finalized_package = PackingService.finalize_package(str(package.id), request.user)
            serializer = PackageSerializer(finalized_package)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Package.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'PACKAGE_NOT_FOUND',
                    'message': 'Package not found in this packing task'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'FINALIZATION_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark a packing task as completed."""
        task = self.get_object()

        try:
            completed_task = PackingService.complete_packing(str(task.id), request.user)
            serializer = PackingTaskDetailSerializer(completed_task)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'COMPLETION_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get packing task summary."""
        task = self.get_object()

        try:
            serializer = self.get_serializer(task)
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
