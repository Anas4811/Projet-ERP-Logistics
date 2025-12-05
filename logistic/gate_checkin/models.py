from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class GateQueue(models.Model):
    """Queue management for gate check-in process."""
    STATUS_CHOICES = [
        ('WAITING', 'Waiting'),
        ('CHECKING_IN', 'Checking In'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ]

    queue_number = models.CharField(max_length=10, unique=True)
    asn = models.ForeignKey('asn_shipment.ASN', on_delete=models.CASCADE, related_name='gate_queues')

    # Vehicle and driver information
    vehicle_number = models.CharField(max_length=20)
    trailer_number = models.CharField(max_length=20, blank=True)
    driver_name = models.CharField(max_length=100)
    driver_id = models.CharField(max_length=20, blank=True)
    driver_phone = models.CharField(max_length=15)
    driver_license = models.CharField(max_length=20, blank=True)

    # Check-in details
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_in_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='checked_in_queues')
    verification_time = models.DateTimeField(null=True, blank=True)
    verification_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_queues')

    # Status and queue management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WAITING')
    priority = models.IntegerField(default=1, help_text='Lower number = higher priority')
    position_in_queue = models.PositiveIntegerField(null=True, blank=True)

    # Verification results
    documents_verified = models.BooleanField(default=False)
    vehicle_inspection_passed = models.BooleanField(default=False)
    cargo_inspection_passed = models.BooleanField(default=False)

    # Notes and issues
    check_in_notes = models.TextField(blank=True)
    verification_notes = models.TextField(blank=True)
    issues_found = models.TextField(blank=True)

    # Timestamps
    estimated_completion_time = models.DateTimeField(null=True, blank=True)
    actual_completion_time = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Queue {self.queue_number} - {self.vehicle_number}"

    def save(self, *args, **kwargs):
        # Auto-generate queue number if not provided
        if not self.queue_number:
            today = timezone.now().date()
            last_queue = GateQueue.objects.filter(
                created_at__date=today
            ).order_by('-id').first()

            if last_queue:
                # Extract number from last queue and increment
                try:
                    last_num = int(last_queue.queue_number.split('-')[-1])
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1

            self.queue_number = f"Q{today.strftime('%Y%m%d')}-{next_num:03d}"

        super().save(*args, **kwargs)

    @property
    def wait_time(self):
        """Calculate wait time from check-in to completion."""
        if self.check_in_time and self.actual_completion_time:
            return self.actual_completion_time - self.check_in_time
        elif self.check_in_time:
            return timezone.now() - self.check_in_time
        return None

    @property
    def is_overdue(self):
        """Check if queue item is overdue."""
        if self.estimated_completion_time and self.status not in ['COMPLETED', 'REJECTED']:
            return timezone.now() > self.estimated_completion_time
        return False

    class Meta:
        ordering = ['priority', 'created_at']
        indexes = [
            models.Index(fields=['queue_number']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['asn']),
        ]


class VehicleInspection(models.Model):
    """Detailed vehicle inspection records."""
    INSPECTION_TYPE_CHOICES = [
        ('PRE_ARRIVAL', 'Pre-Arrival'),
        ('GATE_CHECK', 'Gate Check'),
        ('POST_LOADING', 'Post Loading'),
        ('DEPARTURE', 'Departure'),
    ]

    gate_queue = models.ForeignKey(GateQueue, on_delete=models.CASCADE, related_name='inspections')
    inspection_type = models.CharField(max_length=15, choices=INSPECTION_TYPE_CHOICES)
    inspected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='vehicle_inspections')

    # Vehicle condition
    exterior_condition = models.TextField(blank=True)
    interior_condition = models.TextField(blank=True)
    tire_condition = models.TextField(blank=True)
    brake_condition = models.TextField(blank=True)
    lights_condition = models.TextField(blank=True)

    # Safety equipment
    fire_extinguisher = models.BooleanField(default=False)
    first_aid_kit = models.BooleanField(default=False)
    warning_triangles = models.BooleanField(default=False)
    spare_tire = models.BooleanField(default=False)

    # Overall assessment
    passed_inspection = models.BooleanField(default=False)
    critical_issues = models.TextField(blank=True)
    recommended_actions = models.TextField(blank=True)
    inspection_notes = models.TextField(blank=True)

    # Photos/evidence (you can extend this with file uploads)
    photo_urls = models.JSONField(default=list, blank=True)

    inspected_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.inspection_type} - {self.gate_queue.queue_number}"

    class Meta:
        ordering = ['-inspected_at']


class DocumentVerification(models.Model):
    """Document verification for gate check-in."""
    DOCUMENT_TYPE_CHOICES = [
        ('ASN', 'Advance Shipment Notice'),
        ('PO', 'Purchase Order'),
        ('DELIVERY_NOTE', 'Delivery Note'),
        ('INVOICE', 'Invoice'),
        ('DRIVER_LICENSE', 'Driver License'),
        ('VEHICLE_REGISTRATION', 'Vehicle Registration'),
        ('INSURANCE', 'Insurance Certificate'),
        ('CUSTOMS_DOCS', 'Customs Documents'),
        ('OTHER', 'Other'),
    ]

    gate_queue = models.ForeignKey(GateQueue, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    document_number = models.CharField(max_length=50, blank=True)
    is_present = models.BooleanField(default=False)
    is_valid = models.BooleanField(default=False)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='verified_documents')

    # Verification details
    verification_notes = models.TextField(blank=True)
    issues_found = models.TextField(blank=True)

    # File attachments (you can extend this)
    attachment_urls = models.JSONField(default=list, blank=True)

    verified_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.document_type} - {self.gate_queue.queue_number}"

    class Meta:
        ordering = ['document_type']
        unique_together = ['gate_queue', 'document_type']


class GateLog(models.Model):
    """Log all gate activities for audit purposes."""
    ACTIVITY_CHOICES = [
        ('ARRIVAL', 'Vehicle Arrival'),
        ('CHECK_IN_START', 'Check-in Started'),
        ('DOCUMENT_VERIFICATION', 'Document Verification'),
        ('VEHICLE_INSPECTION', 'Vehicle Inspection'),
        ('APPROVAL', 'Approval Granted'),
        ('REJECTION', 'Entry Rejected'),
        ('DEPARTURE', 'Vehicle Departure'),
        ('OTHER', 'Other Activity'),
    ]

    gate_queue = models.ForeignKey(GateQueue, on_delete=models.CASCADE, related_name='logs')
    activity = models.CharField(max_length=25, choices=ACTIVITY_CHOICES)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='gate_logs')

    description = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    # Additional data (can store JSON for flexible logging)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.activity} - {self.gate_queue.queue_number} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['gate_queue', 'timestamp']),
            models.Index(fields=['activity']),
        ]