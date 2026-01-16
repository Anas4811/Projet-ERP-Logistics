from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Avg
from django.utils import timezone
from .models import Vendor, VendorContact, PurchaseOrder, PurchaseOrderItem, Notification
from .serializers import (
    VendorSerializer, VendorContactSerializer, PurchaseOrderSerializer,
    PurchaseOrderCreateSerializer, PurchaseOrderListSerializer,
    PurchaseOrderItemSerializer, PurchaseOrderApprovalSerializer,
    NotificationSerializer, VendorPerformanceSerializer, POStatusReportSerializer
)


class VendorViewSet(viewsets.ModelViewSet):
    """ViewSet for vendor management."""
    queryset = Vendor.objects.all().order_by('name')
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        status_filter = self.request.query_params.get('status', None)
        preferred = self.request.query_params.get('preferred', None)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(vendor_code__icontains=search) |
                Q(email__icontains=search)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if preferred:
            queryset = queryset.filter(is_preferred=preferred.lower() == 'true')

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def add_contact(self, request, pk=None):
        """Add a contact to a vendor."""
        vendor = self.get_object()
        serializer = VendorContactSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(vendor=vendor)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VendorContactViewSet(viewsets.ModelViewSet):
    """ViewSet for vendor contacts."""
    serializer_class = VendorContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return VendorContact.objects.filter(
            vendor_id=self.kwargs.get('vendor_pk')
        ).order_by('-is_primary', 'name')


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """ViewSet for purchase orders."""
    queryset = PurchaseOrder.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return PurchaseOrderCreateSerializer
        elif self.action == 'list':
            return PurchaseOrderListSerializer
        return PurchaseOrderSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related('vendor', 'created_by', 'approved_by')
        status_filter = self.request.query_params.get('status', None)
        vendor_id = self.request.query_params.get('vendor', None)
        search = self.request.query_params.get('search', None)
        overdue = self.request.query_params.get('overdue', None)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)

        if search:
            queryset = queryset.filter(
                Q(po_number__icontains=search) |
                Q(vendor__name__icontains=search)
            )

        if overdue:
            queryset = queryset.filter(
                expected_delivery_date__lt=timezone.now().date(),
                status__in=['APPROVED', 'ORDERED', 'PARTIALLY_RECEIVED']
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a purchase order."""
        po = self.get_object()
        serializer = PurchaseOrderApprovalSerializer(data=request.data, context={'po': po})

        if serializer.is_valid():
            po.status = 'APPROVED'
            po.approved_by = request.user
            po.approved_at = timezone.now()
            po.approval_notes = serializer.validated_data.get('notes', '')
            po.save()

            # Create notification for PO creator
            Notification.objects.create(
                recipient=po.created_by,
                notification_type='PO_APPROVAL',
                title=f'PO {po.po_number} Approved',
                message=f'Your purchase order {po.po_number} has been approved.',
                related_po=po
            )

            return Response({'message': 'Purchase order approved successfully'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a purchase order."""
        po = self.get_object()
        serializer = PurchaseOrderApprovalSerializer(data=request.data, context={'po': po})

        if serializer.is_valid():
            po.status = 'REJECTED'
            po.approved_by = request.user
            po.approved_at = timezone.now()
            po.approval_notes = serializer.validated_data.get('notes', '')
            po.save()

            # Create notification for PO creator
            Notification.objects.create(
                recipient=po.created_by,
                notification_type='PO_APPROVAL',
                title=f'PO {po.po_number} Rejected',
                message=f'Your purchase order {po.po_number} has been rejected. Reason: {serializer.validated_data.get("notes", "No reason provided")}',
                related_po=po
            )

            return Response({'message': 'Purchase order rejected successfully'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PurchaseOrderItemViewSet(viewsets.ModelViewSet):
    """ViewSet for purchase order items."""
    serializer_class = PurchaseOrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PurchaseOrderItem.objects.filter(
            purchase_order_id=self.kwargs.get('po_pk')
        ).order_by('item_code')


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for notifications."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read."""
        notification = self.get_object()
        if notification.recipient == request.user:
            notification.mark_as_read()
            return Response({'message': 'Notification marked as read'})
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

        return Response({'message': 'All notifications marked as read'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_performance_report(request):
    """Vendor performance report."""
    vendors = Vendor.objects.annotate(
        total_pos=Count('purchase_orders'),
        on_time_deliveries=Count(
            'purchase_orders',
            filter=Q(purchase_orders__actual_delivery_date__lte=Q('purchase_orders__expected_delivery_date'))
        ),
        avg_rating=Avg('rating')
    ).filter(total_pos__gt=0)

    serializer = VendorPerformanceSerializer(vendors, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def po_status_report(request):
    """Purchase order status report."""
    status_counts = PurchaseOrder.objects.values('status').annotate(
        count=Count('status')
    ).order_by('status')

    # Add percentages
    total_pos = sum(item['count'] for item in status_counts)
    for item in status_counts:
        item['percentage'] = round((item['count'] / total_pos * 100), 2) if total_pos > 0 else 0

    # Get overdue POs
    overdue_pos = PurchaseOrder.objects.filter(
        expected_delivery_date__lt=timezone.now().date(),
        status__in=['APPROVED', 'ORDERED', 'PARTIALLY_RECEIVED']
    ).select_related('vendor')[:20]  # Limit to 20 for performance

    overdue_serializer = PurchaseOrderListSerializer(overdue_pos, many=True)

    return Response({
        'status_summary': status_counts,
        'overdue_pos': overdue_serializer.data,
        'total_overdue': overdue_pos.count()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Dashboard statistics for vendor management."""
    total_vendors = Vendor.objects.count()
    active_vendors = Vendor.objects.filter(status='ACTIVE').count()
    total_pos = PurchaseOrder.objects.count()
    pending_pos = PurchaseOrder.objects.filter(status='PENDING_APPROVAL').count()
    overdue_pos = PurchaseOrder.objects.filter(
        expected_delivery_date__lt=timezone.now().date(),
        status__in=['APPROVED', 'ORDERED', 'PARTIALLY_RECEIVED']
    ).count()

    return Response({
        'total_vendors': total_vendors,
        'active_vendors': active_vendors,
        'total_pos': total_pos,
        'pending_pos': pending_pos,
        'overdue_pos': overdue_pos,
        'vendor_activation_rate': round((active_vendors / total_vendors * 100), 2) if total_vendors > 0 else 0
    })
