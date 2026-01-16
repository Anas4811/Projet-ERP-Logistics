from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone
from .models import ASN, ASNItem, ShipmentSchedule, InboundTracking
from .serializers import (
    ASNSerializer, ASNCreateSerializer, ASNListSerializer,
    ASNStatusUpdateSerializer, ASNItemSerializer,
    ShipmentScheduleSerializer, InboundTrackingSerializer,
    ExpectedArrivalsSerializer, DeliveryPerformanceSerializer
)


class ASNViewSet(viewsets.ModelViewSet):
    """ViewSet for ASN management."""
    queryset = ASN.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return ASNCreateSerializer
        elif self.action == 'list':
            return ASNListSerializer
        return ASNSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related('purchase_order', 'vendor', 'created_by', 'approved_by')
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
                Q(asn_number__icontains=search) |
                Q(purchase_order__po_number__icontains=search) |
                Q(vendor__name__icontains=search)
            )

        if overdue:
            queryset = queryset.filter(
                expected_arrival_date__lt=timezone.now().date(),
                status__in=['APPROVED', 'IN_TRANSIT']
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an ASN."""
        asn = self.get_object()

        if asn.status != 'CREATED':
            return Response({'error': 'ASN is not in created status'}, status=status.HTTP_400_BAD_REQUEST)

        asn.status = 'APPROVED'
        asn.approved_by = request.user
        asn.approved_at = timezone.now()
        asn.save()

        return Response({'message': 'ASN approved successfully'})

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update ASN status."""
        asn = self.get_object()
        serializer = ASNStatusUpdateSerializer(data=request.data)

        if serializer.is_valid():
            old_status = asn.status
            asn.status = serializer.validated_data['status']

            if 'actual_ship_date' in serializer.validated_data:
                asn.actual_ship_date = serializer.validated_data['actual_ship_date']

            if 'actual_arrival_date' in serializer.validated_data:
                asn.actual_arrival_date = serializer.validated_data['actual_arrival_date']

            asn.save()

            # Create tracking record if status changed to IN_TRANSIT
            if old_status != 'IN_TRANSIT' and asn.status == 'IN_TRANSIT':
                InboundTracking.objects.get_or_create(
                    asn=asn,
                    defaults={'current_location': 'In Transit'}
                )

            return Response({'message': 'ASN status updated successfully'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def create_from_po(self, request):
        """Create ASN from existing PO."""
        po_id = request.data.get('po_id')
        if not po_id:
            return Response({'error': 'PO ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from vendor_management.models import PurchaseOrder
            po = PurchaseOrder.objects.get(id=po_id, status='APPROVED')

            # Create ASN
            asn = ASN.objects.create(
                purchase_order=po,
                vendor=po.vendor,
                expected_ship_date=timezone.now().date(),
                expected_arrival_date=po.expected_delivery_date or timezone.now().date(),
                created_by=request.user
            )

            # Create ASN items
            for po_item in po.items.all():
                ASNItem.objects.create(
                    asn=asn,
                    purchase_order_item=po_item,
                    item_code=po_item.item_code,
                    item_description=po_item.item_description,
                    quantity_expected=po_item.quantity_ordered - po_item.quantity_received,
                    unit_price=po_item.unit_price,
                )

            serializer = ASNSerializer(asn)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except PurchaseOrder.DoesNotExist:
            return Response({'error': 'PO not found or not approved'}, status=status.HTTP_404_NOT_FOUND)


class ASNItemViewSet(viewsets.ModelViewSet):
    """ViewSet for ASN items."""
    serializer_class = ASNItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ASNItem.objects.filter(
            asn_id=self.kwargs.get('asn_pk')
        ).order_by('item_code')

    def perform_update(self, serializer):
        """Update ASN item and mark as received if quantity matches."""
        instance = serializer.save()

        # Update received_by and received_at if quantity was updated
        if 'quantity_received' in serializer.validated_data:
            instance.received_by = self.request.user
            instance.received_at = timezone.now()
            instance.save()


class ShipmentScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet for shipment schedules."""
    queryset = ShipmentSchedule.objects.filter(is_active=True).order_by('vendor__name')
    serializer_class = ShipmentScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        vendor_id = self.request.query_params.get('vendor', None)

        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)

        return queryset


class InboundTrackingViewSet(viewsets.ModelViewSet):
    """ViewSet for inbound tracking."""
    queryset = InboundTracking.objects.all().order_by('-updated_at')
    serializer_class = InboundTrackingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset().select_related('asn__vendor')
        asn_id = self.request.query_params.get('asn', None)

        if asn_id:
            queryset = queryset.filter(asn_id=asn_id)

        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expected_arrivals_report(request):
    """Expected arrivals report."""
    # Get ASNs expected to arrive in the next 7 days
    end_date = timezone.now().date() + timezone.timedelta(days=7)
    asns = ASN.objects.filter(
        expected_arrival_date__lte=end_date,
        status__in=['APPROVED', 'IN_TRANSIT']
    ).select_related('vendor', 'purchase_order').order_by('expected_arrival_date')

    serializer = ExpectedArrivalsSerializer(asns, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def delivery_performance_report(request):
    """Delivery performance report."""
    # Get completed ASNs from last 30 days
    start_date = timezone.now().date() - timezone.timedelta(days=30)
    completed_asns = ASN.objects.filter(
        actual_arrival_date__gte=start_date,
        status='RECEIVED'
    ).select_related('vendor')

    performance_data = []
    on_time_count = 0
    total_count = completed_asns.count()

    for asn in completed_asns:
        days_variance = (asn.actual_arrival_date - asn.expected_arrival_date).days
        on_time = days_variance <= 0
        if on_time:
            on_time_count += 1

        performance_data.append({
            'asn_number': asn.asn_number,
            'vendor_name': asn.vendor.name,
            'expected_date': asn.expected_arrival_date,
            'actual_date': asn.actual_arrival_date,
            'days_variance': days_variance,
            'status': asn.status,
            'on_time': on_time
        })

    on_time_percentage = round((on_time_count / total_count * 100), 2) if total_count > 0 else 0

    return Response({
        'performance_data': performance_data,
        'summary': {
            'total_deliveries': total_count,
            'on_time_deliveries': on_time_count,
            'on_time_percentage': on_time_percentage,
            'average_variance': sum(item['days_variance'] for item in performance_data) / total_count if total_count > 0 else 0
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Dashboard statistics for ASN management."""
    total_asns = ASN.objects.count()
    in_transit = ASN.objects.filter(status='IN_TRANSIT').count()
    expected_today = ASN.objects.filter(
        expected_arrival_date=timezone.now().date(),
        status__in=['APPROVED', 'IN_TRANSIT']
    ).count()
    overdue = ASN.objects.filter(
        expected_arrival_date__lt=timezone.now().date(),
        status__in=['APPROVED', 'IN_TRANSIT']
    ).count()

    # Recent ASNs
    recent_asns = ASN.objects.select_related('vendor').order_by('-created_at')[:5]
    recent_serializer = ASNListSerializer(recent_asns, many=True)

    return Response({
        'total_asns': total_asns,
        'in_transit': in_transit,
        'expected_today': expected_today,
        'overdue': overdue,
        'recent_asns': recent_serializer.data
    })
