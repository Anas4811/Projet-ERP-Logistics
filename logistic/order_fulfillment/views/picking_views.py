"""
Picking views for Order Fulfillment & Distribution.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import PickingTask
from ..services import PickingService
from ..serializers.picking_serializers import (
    PickingTaskListSerializer, PickingTaskDetailSerializer,
    PickingTaskAssignSerializer, PickingQuantityUpdateSerializer,
    PickingTaskSummarySerializer
)
from ..permissions import IsWarehouseStaff


class PickingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Picking Task management.

    Provides CRUD operations and workflow actions for picking tasks.
    """

    queryset = PickingTask.objects.all()
    permission_classes = [IsWarehouseStaff]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return PickingTaskListSerializer
        elif self.action == 'summary':
            return PickingTaskSummarySerializer
        elif self.action == 'assign_picker':
            return PickingTaskAssignSerializer
        elif self.action == 'update_picked':
            return PickingQuantityUpdateSerializer
        else:
            return PickingTaskDetailSerializer

    @action(detail=True, methods=['post'])
    def assign_picker(self, request, pk=None):
        """Assign a picker to a picking task."""
        task = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            picker = User.objects.get(id=serializer.validated_data['picker_id'])

            updated_task = PickingService.assign_picker(str(task.id), picker, request.user)
            serializer = PickingTaskDetailSerializer(updated_task)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'ASSIGNMENT_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_picked(self, request, pk=None):
        """Update picked quantities for items in a task."""
        task = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = PickingService.update_picked_quantity(
                str(task.id), serializer.validated_data['item_updates'], request.user
            )
            return Response({
                'success': True,
                'data': result
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': {
                    'code': 'UPDATE_FAILED',
                    'message': str(e)
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark a picking task as completed."""
        task = self.get_object()

        try:
            completed_task = PickingService.complete_picking(str(task.id), request.user)
            serializer = PickingTaskDetailSerializer(completed_task)
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
        """Get picking task summary."""
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
