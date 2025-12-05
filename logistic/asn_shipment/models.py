from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class ASN(models.Model):
    """Advance Shipment Notice model."""
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('APPROVED', 'Approved'),
        ('IN_TRANSIT', 'In Transit'),
        ('ARRIVED', 'Arrived'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected'),
    ]

    asn_number = models.CharField(max_length=20, unique=True, help_text='Unique ASN identifier')
    purchase_order = models.ForeignKey('vendor_management.PurchaseOrder', on_delete=models.CASCADE, related_name='asns')
    vendor = models.ForeignKey('vendor_management.Vendor', on_delete=models.CASCADE, related_name='asns')

    # Shipment details
    carrier_name = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=50, blank=True)
    vehicle_number = models.CharField(max_length=20, blank=True)
    driver_name = models.CharField(max_length=100, blank=True)
    driver_phone = models.CharField(max_length=15, blank=True)

    # Dates
    expected_ship_date = models.DateField()
    actual_ship_date = models.DateField(null=True, blank=True)
    expected_arrival_date = models.DateField()
    actual_arrival_date = models.DateField(null=True, blank=True)

    # Status and approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CREATED')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_asns')
    approved_at = models.DateTimeField(null=True, blank=True)

    # Additional information
    notes = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)

    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_asns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ASN-{self.asn_number} - {self.vendor.name}"

    def save(self, *args, **kwargs):
        # Auto-generate ASN number if not provided
        if not self.asn_number:
            last_asn = ASN.objects.order_by('-id').first()
            next_number = (last_asn.id + 1) if last_asn else 1
            self.asn_number = f"ASN{next_number:06d}"
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if ASN is overdue."""
        if self.status not in ['ARRIVED', 'RECEIVED', 'CANCELLED']:
            return timezone.now().date() > self.expected_arrival_date
        return False

    @property
    def total_items(self):
        """Get total number of items in ASN."""
        return self.items.count()

    @property
    def total_quantity(self):
        """Get total quantity across all items."""
        return sum(item.quantity_expected for item in self.items.all())

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['asn_number']),
            models.Index(fields=['status']),
            models.Index(fields=['expected_arrival_date']),
            models.Index(fields=['vendor']),
        ]


class ASNItem(models.Model):
    """Individual items within an ASN."""
    asn = models.ForeignKey(ASN, on_delete=models.CASCADE, related_name='items')
    purchase_order_item = models.ForeignKey('vendor_management.PurchaseOrderItem', on_delete=models.CASCADE, related_name='asn_items')

    # Quantities
    quantity_expected = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Item details (may differ from PO)
    item_code = models.CharField(max_length=50)
    item_description = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Quality and condition
    condition = models.CharField(max_length=50, blank=True, help_text='Item condition upon arrival')
    quality_notes = models.TextField(blank=True)
    has_damage = models.BooleanField(default=False)
    damage_description = models.TextField(blank=True)

    # Tracking
    batch_number = models.CharField(max_length=50, blank=True)
    serial_numbers = models.TextField(blank=True, help_text='Comma-separated serial numbers')
    expiry_date = models.DateField(null=True, blank=True)

    # Receiving details
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_asn_items')
    received_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.item_code} - ASN-{self.asn.asn_number}"

    @property
    def quantity_pending(self):
        """Calculate pending quantity."""
        return self.quantity_expected - self.quantity_received

    @property
    def is_fully_received(self):
        """Check if item is fully received."""
        return self.quantity_received >= self.quantity_expected

    class Meta:
        ordering = ['item_code']


class ShipmentSchedule(models.Model):
    """Schedule for inbound shipments."""
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('BIWEEKLY', 'Bi-weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('CUSTOM', 'Custom'),
    ]

    vendor = models.ForeignKey('vendor_management.Vendor', on_delete=models.CASCADE, related_name='shipment_schedules')
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='WEEKLY')
    day_of_week = models.IntegerField(null=True, blank=True, help_text='0=Monday, 6=Sunday')
    day_of_month = models.IntegerField(null=True, blank=True, help_text='1-31')

    # Time window
    preferred_time_start = models.TimeField(null=True, blank=True)
    preferred_time_end = models.TimeField(null=True, blank=True)

    # Default shipment details
    default_carrier = models.CharField(max_length=100, blank=True)
    default_driver = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.vendor.name} - {self.get_frequency_display()} schedule"

    class Meta:
        ordering = ['vendor__name']


class InboundTracking(models.Model):
    """Track inbound shipments in real-time."""
    asn = models.OneToOneField(ASN, on_delete=models.CASCADE, related_name='tracking')

    # Location tracking
    current_location = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Status updates
    last_status_update = models.DateTimeField(null=True, blank=True)
    status_notes = models.TextField(blank=True)

    # ETA calculations
    estimated_arrival = models.DateTimeField(null=True, blank=True)
    delay_reason = models.TextField(blank=True)

    # Communication
    last_contact = models.DateTimeField(null=True, blank=True)
    contact_person = models.CharField(max_length=100, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tracking for ASN-{self.asn.asn_number}"

    class Meta:
        ordering = ['-updated_at']