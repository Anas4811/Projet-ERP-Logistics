from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Avg
from django.utils import timezone
from .models import GateQueue, VehicleInspection, DocumentVerification, GateLog
from .serializers import (
    GateQueueSerializer, GateQueueCreateSerializer, GateQueueListSerializer,
    VehicleInspectionSerializer, DocumentVerificationSerializer, GateLogSerializer,
    GateCheckInSerializer, GateVerificationSerializer, GateCompleteSerializer,
    GateDashboardSerializer, QueueStatusSerializer, QueuePositionSerializer
)


class GateQueueViewSet(viewsets.ModelViewSet):
    """ViewSet for gate queue management."""
    queryset = GateQueue.objects.all().order_by('priority', 'created_at')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return GateQueueCreateSerializer
        elif self.action == 'list':
            return GateQueueListSerializer
        return GateQueueSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related('asn__vendor', 'check_in_by', 'verification_by')
        status_filter = self.request.query_params.get('status', None)
        search = self.request.query_params.get('search', None)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if search:
            queryset = queryset.filter(
                Q(queue_number__icontains=search) |
                Q(vehicle_number__icontains=search) |
                Q(driver_name__icontains=search) |
                Q(asn__asn_number__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(check_in_by=self.request.user)

    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """Check-in vehicle at gate."""
        queue_item = self.get_object()
        serializer = GateCheckInSerializer(data=request.data)

        if serializer.is_valid():
            queue_item.status = 'CHECKING_IN'
            queue_item.check_in_time = timezone.now()
            queue_item.check_in_by = request.user
            queue_item.check_in_notes = serializer.validated_data.get('check_in_notes', '')
            queue_item.save()

            # Log check-in
            GateLog.objects.create(
                gate_queue=queue_item,
                activity='CHECK_IN_START',
                performed_by=request.user,
                description='Check-in process started.'
            )

            return Response({'message': 'Vehicle checked in successfully'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify documents and vehicle."""
        queue_item = self.get_object()
        serializer = GateVerificationSerializer(data=request.data)

        if serializer.is_valid():
            queue_item.status = 'VERIFIED'
            queue_item.verification_time = timezone.now()
            queue_item.verification_by = request.user
            queue_item.documents_verified = serializer.validated_data['documents_verified']
            queue_item.vehicle_inspection_passed = serializer.validated_data['vehicle_inspection_passed']
            queue_item.cargo_inspection_passed = serializer.validated_data['cargo_inspection_passed']
            queue_item.verification_notes = serializer.validated_data.get('verification_notes', '')
            queue_item.save()

            # Log verification
            GateLog.objects.create(
                gate_queue=queue_item,
                activity='APPROVAL',
                performed_by=request.user,
                description='Document and vehicle verification completed.'
            )

            return Response({'message': 'Verification completed successfully'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete gate check-in process."""
        queue_item = self.get_object()
        serializer = GateCompleteSerializer(data=request.data)

        if serializer.is_valid():
            queue_item.status = 'COMPLETED'
            queue_item.actual_completion_time = timezone.now()
            queue_item.save()

            # Update ASN status if applicable
            if queue_item.asn.status == 'IN_TRANSIT':
                queue_item.asn.status = 'ARRIVED'
                queue_item.asn.actual_arrival_date = timezone.now().date()
                queue_item.asn.save()

            # Log completion
            GateLog.objects.create(
                gate_queue=queue_item,
                activity='DEPARTURE',
                performed_by=request.user,
                description='Gate check-in process completed.'
            )

            return Response({'message': 'Gate check-in completed successfully'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VehicleInspectionViewSet(viewsets.ModelViewSet):
    """ViewSet for vehicle inspections."""
    serializer_class = VehicleInspectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = VehicleInspection.objects.select_related('gate_queue', 'inspected_by')
        queue_id = self.request.query_params.get('queue', None)

        if queue_id:
            queryset = queryset.filter(gate_queue_id=queue_id)

        return queryset.order_by('-inspected_at')

    def perform_create(self, serializer):
        serializer.save(inspected_by=self.request.user)


class DocumentVerificationViewSet(viewsets.ModelViewSet):
    """ViewSet for document verification."""
    serializer_class = DocumentVerificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = DocumentVerification.objects.select_related('gate_queue', 'verified_by')
        queue_id = self.request.query_params.get('queue', None)
        doc_type = self.request.query_params.get('type', None)

        if queue_id:
            queryset = queryset.filter(gate_queue_id=queue_id)

        if doc_type:
            queryset = queryset.filter(document_type=doc_type)

        return queryset.order_by('-verified_at')

    def perform_create(self, serializer):
        serializer.save(verified_by=self.request.user)


class GateLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for gate logs."""
    queryset = GateLog.objects.all().order_by('-timestamp')
    serializer_class = GateLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset().select_related('gate_queue', 'performed_by')
        queue_id = self.request.query_params.get('queue', None)
        activity = self.request.query_params.get('activity', None)

        if queue_id:
            queryset = queryset.filter(gate_queue_id=queue_id)

        if activity:
            queryset = queryset.filter(activity=activity)

        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """Gate dashboard with real-time status."""
    # Current queue status
    waiting_count = GateQueue.objects.filter(status='WAITING').count()
    checking_count = GateQueue.objects.filter(status='CHECKING_IN').count()
    verified_count = GateQueue.objects.filter(status='VERIFIED').count()
    completed_today = GateQueue.objects.filter(
        status='COMPLETED',
        created_at__date=timezone.now().date()
    ).count()

    # Recent activity
    recent_queue = GateQueue.objects.select_related('asn__vendor').order_by('-created_at')[:10]
    recent_serializer = GateQueueListSerializer(recent_queue, many=True)

    dashboard_data = {
        'waiting_count': waiting_count,
        'checking_count': checking_count,
        'verified_count': verified_count,
        'completed_today': completed_today,
        'recent_queue': recent_serializer.data
    }

    return Response(dashboard_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def queue_status(request):
    """API endpoint for queue status."""
    status_counts = GateQueue.objects.values('status').annotate(
        count=Count('status')
    )

    data = {item['status']: item['count'] for item in status_counts}
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def queue_position(request, pk):
    """API endpoint for queue position."""
    try:
        queue_item = GateQueue.objects.get(pk=pk)

        # Calculate position in queue
        position = GateQueue.objects.filter(
            status='WAITING',
            created_at__lt=queue_item.created_at
        ).count() + 1

        data = {
            'position': position,
            'status': queue_item.status,
            'estimated_wait': None  # Could implement wait time estimation
        }

        return Response(data)

    except GateQueue.DoesNotExist:
        return Response({'error': 'Queue item not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def performance_report(request):
    """Queue performance report."""
    # Performance metrics for last 30 days
    start_date = timezone.now() - timezone.timedelta(days=30)
    completed_queues = GateQueue.objects.filter(
        actual_completion_time__gte=start_date,
        status='COMPLETED'
    )

    total_processed = completed_queues.count()
    avg_daily_processed = total_processed / 30 if total_processed > 0 else 0

    # Calculate average processing time
    avg_processing_time = None
    if completed_queues.exists():
        avg_time = completed_queues.aggregate(
            avg_time=Avg('actual_completion_time') - Avg('check_in_time')
        )['avg_time']
        avg_processing_time = str(avg_time) if avg_time else None

    return Response({
        'total_processed': total_processed,
        'avg_processing_time': avg_processing_time,
        'avg_daily_processed': round(avg_daily_processed, 2),
        'total_waiting': GateQueue.objects.filter(status='WAITING').count(),
        'total_overdue': GateQueue.objects.filter(
            estimated_completion_time__lt=timezone.now(),
            status__in=['WAITING', 'CHECKING_IN', 'VERIFIED']
        ).count()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_activity_report(request):
    """Daily activity report."""
    today = timezone.now().date()

    # Today's queues
    today_queues = GateQueue.objects.filter(
        created_at__date=today
    ).select_related('asn__vendor')

    # Today's logs
    today_logs = GateLog.objects.filter(
        timestamp__date=today
    ).select_related('gate_queue', 'performed_by').order_by('-timestamp')[:50]

    queues_serializer = GateQueueListSerializer(today_queues, many=True)
    logs_serializer = GateLogSerializer(today_logs, many=True)

    return Response({
        'date': today,
        'total_entries': today_queues.count(),
        'completed_entries': today_queues.filter(status='COMPLETED').count(),
        'queues': queues_serializer.data,
        'logs': logs_serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_create_inspections(request, queue_id):
    """Bulk create vehicle inspections for a queue."""
    try:
        queue = GateQueue.objects.get(id=queue_id)
        inspections_data = request.data.get('inspections', [])

        created_inspections = []
        for inspection_data in inspections_data:
            inspection_data['gate_queue'] = queue.id
            serializer = VehicleInspectionSerializer(data=inspection_data)
            if serializer.is_valid():
                inspection = serializer.save(inspected_by=request.user)
                created_inspections.append(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': f'Created {len(created_inspections)} inspections',
            'inspections': created_inspections
        }, status=status.HTTP_201_CREATED)

    except GateQueue.DoesNotExist:
        return Response({'error': 'Queue not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_verify_documents(request, queue_id):
    """Bulk create document verifications for a queue."""
    try:
        queue = GateQueue.objects.get(id=queue_id)
        documents_data = request.data.get('documents', [])

        created_documents = []
        for doc_data in documents_data:
            doc_data['gate_queue'] = queue.id
            serializer = DocumentVerificationSerializer(data=doc_data)
            if serializer.is_valid():
                document = serializer.save(verified_by=request.user)
                created_documents.append(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': f'Verified {len(created_documents)} documents',
            'documents': created_documents
        }, status=status.HTTP_201_CREATED)

    except GateQueue.DoesNotExist:
        return Response({'error': 'Queue not found'}, status=status.HTTP_404_NOT_FOUND)
