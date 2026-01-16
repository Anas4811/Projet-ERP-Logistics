from rest_framework import serializers
from .models import GateQueue, VehicleInspection, DocumentVerification, GateLog


class VehicleInspectionSerializer(serializers.ModelSerializer):
    """Serializer for vehicle inspections."""
    gate_queue_number = serializers.CharField(source='gate_queue.queue_number', read_only=True)
    inspected_by_name = serializers.CharField(source='inspected_by.get_full_name', read_only=True)

    class Meta:
        model = VehicleInspection
        fields = [
            'id', 'gate_queue', 'gate_queue_number', 'inspection_type',
            'inspected_by', 'inspected_by_name', 'exterior_condition',
            'interior_condition', 'tire_condition', 'brake_condition',
            'lights_condition', 'fire_extinguisher', 'first_aid_kit',
            'warning_triangles', 'spare_tire', 'passed_inspection',
            'critical_issues', 'recommended_actions', 'inspection_notes',
            'photo_urls', 'inspected_at'
        ]
        read_only_fields = ['inspected_at']


class DocumentVerificationSerializer(serializers.ModelSerializer):
    """Serializer for document verification."""
    gate_queue_number = serializers.CharField(source='gate_queue.queue_number', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)

    class Meta:
        model = DocumentVerification
        fields = [
            'id', 'gate_queue', 'gate_queue_number', 'document_type',
            'document_number', 'is_present', 'is_valid', 'verified_by',
            'verified_by_name', 'verification_notes', 'issues_found',
            'attachment_urls', 'verified_at'
        ]
        read_only_fields = ['verified_at']


class GateLogSerializer(serializers.ModelSerializer):
    """Serializer for gate logs."""
    gate_queue_number = serializers.CharField(source='gate_queue.queue_number', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)

    class Meta:
        model = GateLog
        fields = [
            'id', 'gate_queue', 'gate_queue_number', 'activity', 'performed_by',
            'performed_by_name', 'description', 'timestamp', 'metadata'
        ]
        read_only_fields = ['timestamp']


class GateQueueSerializer(serializers.ModelSerializer):
    """Serializer for gate queues."""
    asn_number = serializers.CharField(source='asn.asn_number', read_only=True)
    vendor_name = serializers.CharField(source='asn.vendor.name', read_only=True)
    vehicle_inspections = VehicleInspectionSerializer(many=True, read_only=True)
    documents = DocumentVerificationSerializer(many=True, read_only=True)
    logs = GateLogSerializer(many=True, read_only=True)
    wait_time = serializers.CharField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = GateQueue
        fields = [
            'id', 'queue_number', 'asn', 'asn_number', 'vendor_name',
            'vehicle_number', 'trailer_number', 'driver_name', 'driver_id',
            'driver_phone', 'driver_license', 'check_in_time', 'check_in_by',
            'verification_time', 'verification_by', 'status', 'priority',
            'position_in_queue', 'documents_verified', 'vehicle_inspection_passed',
            'cargo_inspection_passed', 'check_in_notes', 'verification_notes',
            'issues_found', 'estimated_completion_time', 'actual_completion_time',
            'created_at', 'updated_at', 'vehicle_inspections', 'documents', 'logs',
            'wait_time', 'is_overdue'
        ]
        read_only_fields = ['queue_number', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['check_in_by'] = self.context['request'].user
        return super().create(validated_data)


class GateQueueCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating gate queue entries."""
    class Meta:
        model = GateQueue
        fields = [
            'asn', 'vehicle_number', 'trailer_number', 'driver_name',
            'driver_id', 'driver_phone', 'driver_license'
        ]

    def create(self, validated_data):
        validated_data['check_in_by'] = self.context['request'].user
        return super().create(validated_data)


class GateQueueListSerializer(serializers.ModelSerializer):
    """Simplified serializer for gate queue lists."""
    asn_number = serializers.CharField(source='asn.asn_number', read_only=True)
    vendor_name = serializers.CharField(source='asn.vendor.name', read_only=True)
    wait_time = serializers.CharField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = GateQueue
        fields = [
            'id', 'queue_number', 'asn_number', 'vendor_name', 'vehicle_number',
            'driver_name', 'status', 'priority', 'created_at', 'check_in_time',
            'wait_time', 'is_overdue'
        ]


class GateCheckInSerializer(serializers.Serializer):
    """Serializer for gate check-in."""
    check_in_notes = serializers.CharField(required=False, allow_blank=True)


class GateVerificationSerializer(serializers.Serializer):
    """Serializer for gate verification."""
    documents_verified = serializers.BooleanField(default=False)
    vehicle_inspection_passed = serializers.BooleanField(default=False)
    cargo_inspection_passed = serializers.BooleanField(default=False)
    verification_notes = serializers.CharField(required=False, allow_blank=True)


class GateCompleteSerializer(serializers.Serializer):
    """Serializer for completing gate check-in."""
    pass


class GateDashboardSerializer(serializers.Serializer):
    """Serializer for gate dashboard data."""
    waiting_count = serializers.IntegerField()
    checking_count = serializers.IntegerField()
    verified_count = serializers.IntegerField()
    completed_today = serializers.IntegerField()
    recent_queue = GateQueueListSerializer(many=True)


class QueueStatusSerializer(serializers.Serializer):
    """Serializer for queue status API."""
    status = serializers.CharField()
    count = serializers.IntegerField()


class QueuePositionSerializer(serializers.Serializer):
    """Serializer for queue position API."""
    position = serializers.IntegerField()
    status = serializers.CharField()
    estimated_wait = serializers.IntegerField(required=False)


class GatePerformanceSerializer(serializers.Serializer):
    """Serializer for gate performance reports."""
    total_processed = serializers.IntegerField()
    avg_processing_time = serializers.DurationField(required=False)
    avg_daily_processed = serializers.IntegerField()
    total_waiting = serializers.IntegerField()
    total_overdue = serializers.IntegerField()


class DailyActivitySerializer(serializers.Serializer):
    """Serializer for daily activity reports."""
    date = serializers.DateField()
    total_entries = serializers.IntegerField()
    completed_entries = serializers.IntegerField()
    avg_wait_time = serializers.DurationField()
    peak_hours = serializers.ListField(child=serializers.IntegerField())
