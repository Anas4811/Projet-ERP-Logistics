from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class Vendor(models.Model):
    """Vendor/Supplier model for managing external suppliers."""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('SUSPENDED', 'Suspended'),
        ('BLACKLISTED', 'Blacklisted'),
    ]

    name = models.CharField(max_length=200, unique=True)
    vendor_code = models.CharField(max_length=20, unique=True, help_text='Unique vendor identifier')
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True)

    # Business details
    tax_id = models.CharField(max_length=50, blank=True, help_text='Tax identification number')
    registration_number = models.CharField(max_length=50, blank=True)
    payment_terms = models.CharField(max_length=100, default='Net 30', help_text='Payment terms (e.g., Net 30, COD)')

    # Performance metrics
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, help_text='Vendor rating (0-5)')
    on_time_delivery_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text='Percentage')
    quality_rating = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text='Percentage')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    is_preferred = models.BooleanField(default=False, help_text='Preferred vendor status')

    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_vendors')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.vendor_code})"

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['vendor_code']),
            models.Index(fields=['status']),
            models.Index(fields=['is_preferred']),
        ]


class VendorContact(models.Model):
    """Additional contacts for vendors."""
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    is_primary = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.vendor.name}"

    class Meta:
        ordering = ['-is_primary', 'name']


class PurchaseOrder(models.Model):
    """Purchase Order model for managing vendor orders."""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('ORDERED', 'Ordered'),
        ('PARTIALLY_RECEIVED', 'Partially Received'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]

    po_number = models.CharField(max_length=20, unique=True, help_text='Unique PO number')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='purchase_orders')

    # Order details
    order_date = models.DateField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)

    # Financial details
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Status and approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_pos')
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)

    # Additional info
    shipping_address = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_pos')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PO-{self.po_number} - {self.vendor.name}"

    def save(self, *args, **kwargs):
        # Auto-generate PO number if not provided
        if not self.po_number:
            # Simple PO number generation - you might want to make this more sophisticated
            last_po = PurchaseOrder.objects.order_by('-id').first()
            next_number = (last_po.id + 1) if last_po else 1
            self.po_number = f"PO{next_number:06d}"
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        """Check if PO is overdue."""
        if self.expected_delivery_date and self.status not in ['RECEIVED', 'CANCELLED']:
            return timezone.now().date() > self.expected_delivery_date
        return False

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['po_number']),
            models.Index(fields=['status']),
            models.Index(fields=['vendor']),
            models.Index(fields=['order_date']),
        ]


class PurchaseOrderItem(models.Model):
    """Individual items within a purchase order."""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    item_code = models.CharField(max_length=50)
    item_description = models.CharField(max_length=200)
    quantity_ordered = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    # Tracking
    expected_delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.item_code} - {self.purchase_order.po_number}"

    @property
    def quantity_pending(self):
        """Calculate pending quantity."""
        return self.quantity_ordered - self.quantity_received

    @property
    def is_fully_received(self):
        """Check if item is fully received."""
        return self.quantity_received >= self.quantity_ordered

    class Meta:
        ordering = ['item_code']


class Notification(models.Model):
    """Notification system for PO updates and alerts."""
    TYPE_CHOICES = [
        ('PO_APPROVAL', 'Purchase Order Approval'),
        ('PO_OVERDUE', 'Purchase Order Overdue'),
        ('DELIVERY_REMINDER', 'Delivery Reminder'),
        ('VENDOR_UPDATE', 'Vendor Information Update'),
        ('SYSTEM_ALERT', 'System Alert'),
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')

    title = models.CharField(max_length=200)
    message = models.TextField()
    related_po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, null=True, blank=True)
    related_vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.recipient}"

    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
        ]