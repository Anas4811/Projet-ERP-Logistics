from django.contrib import admin
from .models import GateQueue, VehicleInspection, DocumentVerification, GateLog


@admin.register(GateQueue)
class GateQueueAdmin(admin.ModelAdmin):
    list_display = ['queue_number', 'asn', 'vehicle_number', 'driver_name', 'status', 'priority', 'created_at', 'wait_time']
    list_filter = ['status', 'priority', 'created_at', 'check_in_time']
    search_fields = ['queue_number', 'vehicle_number', 'driver_name', 'asn__asn_number']
    ordering = ['priority', 'created_at']
    readonly_fields = ['queue_number']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('asn', 'check_in_by', 'verification_by')

    def wait_time(self, obj):
        return obj.wait_time if obj.wait_time else None
    wait_time.short_description = 'Wait Time'


@admin.register(VehicleInspection)
class VehicleInspectionAdmin(admin.ModelAdmin):
    list_display = ['gate_queue', 'inspection_type', 'inspected_by', 'passed_inspection', 'inspected_at']
    list_filter = ['inspection_type', 'passed_inspection', 'inspected_at']
    search_fields = ['gate_queue__queue_number', 'inspected_by__email']
    ordering = ['-inspected_at']


@admin.register(DocumentVerification)
class DocumentVerificationAdmin(admin.ModelAdmin):
    list_display = ['gate_queue', 'document_type', 'is_present', 'is_valid', 'verified_by', 'verified_at']
    list_filter = ['document_type', 'is_present', 'is_valid', 'verified_at']
    search_fields = ['gate_queue__queue_number', 'document_number', 'verified_by__email']
    ordering = ['-verified_at']


@admin.register(GateLog)
class GateLogAdmin(admin.ModelAdmin):
    list_display = ['gate_queue', 'activity', 'performed_by', 'timestamp']
    list_filter = ['activity', 'timestamp', 'performed_by']
    search_fields = ['gate_queue__queue_number', 'performed_by__email', 'description']
    ordering = ['-timestamp']
    readonly_fields = ['gate_queue', 'activity', 'performed_by', 'description', 'timestamp', 'metadata']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
