"""
Audit log model for Order Fulfillment & Distribution.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class AuditLog(models.Model):
    """
    Generic audit log for tracking changes to orders, tasks, and shipments.

    Provides comprehensive audit trail for compliance and debugging.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Entity being audited
    entity_type = models.CharField(
        max_length=50,
        help_text="Type of entity (Order, PickingTask, Shipment, etc.)"
    )
    entity_id = models.UUIDField(
        help_text="UUID of the entity being audited"
    )

    # Action performed
    action = models.CharField(
        max_length=50,
        help_text="Action performed (created, updated, status_changed, etc.)"
    )

    # User who performed the action
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        help_text="User who performed the action"
    )

    # Before and after states
    old_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="Previous values before the change"
    )
    new_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="New values after the change"
    )

    # Change details
    field_changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Specific fields that were changed"
    )

    # Context information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Metadata
    timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the change"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional audit metadata"
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.entity_type} {self.entity_id} - {self.action} by {self.user} at {self.timestamp}"

    @classmethod
    def log_change(cls, entity, action: str, user=None, old_values=None,
                   new_values=None, field_changes=None, notes="", metadata=None):
        """
        Create an audit log entry for an entity change.

        Args:
            entity: The model instance being audited
            action: The action performed
            user: User who performed the action
            old_values: Previous state
            new_values: New state
            field_changes: Specific field changes
            notes: Additional notes
            metadata: Additional metadata
        """
        # Convert Decimal objects to strings for JSON serialization
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                return str(obj)
            else:
                return obj

        return cls.objects.create(
            entity_type=entity.__class__.__name__,
            entity_id=entity.id,
            action=action,
            user=user,
            old_values=convert_decimals(old_values or {}),
            new_values=convert_decimals(new_values or {}),
            field_changes=convert_decimals(field_changes or {}),
            notes=notes,
            metadata=convert_decimals(metadata or {})
        )

    @classmethod
    def log_status_change(cls, entity, old_status: str, new_status: str, user=None, notes=""):
        """
        Log a status change for an entity.

        Args:
            entity: The model instance
            old_status: Previous status
            new_status: New status
            user: User making the change
            notes: Additional notes
        """
        return cls.log_change(
            entity=entity,
            action='status_changed',
            user=user,
            old_values={'status': old_status},
            new_values={'status': new_status},
            field_changes={'status': {'old': old_status, 'new': new_status}},
            notes=notes
        )
