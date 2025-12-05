from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager for the User model."""

    def create_user(self, email, username, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, username, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, username, password, **extra_fields)


class Role(models.Model):
    """Role model for RBAC system."""
    ADMIN = 'admin'
    WAREHOUSE = 'warehouse'
    OPERATOR = 'operator'
    DRIVER = 'driver'
    VENDOR = 'vendor'

    ROLE_CHOICES = [
        (ADMIN, 'Administrator'),
        (WAREHOUSE, 'Warehouse Staff'),
        (OPERATOR, 'Operations Staff'),
        (DRIVER, 'Driver'),
        (VENDOR, 'Vendor'),
    ]

    name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        help_text='Specific permissions for this role'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_name_display()

    class Meta:
        ordering = ['name']


class User(AbstractUser):
    """Custom user model extending Django's AbstractUser."""
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(max_length=15, blank=True)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True)
    roles = models.ManyToManyField(Role, blank=True, related_name='users')

    # Override username to make it optional, email is primary
    username = models.CharField(max_length=150, unique=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.email} ({self.get_full_name() or self.username})"

    def get_primary_role(self):
        """Get the user's primary role (first one assigned)."""
        return self.roles.first()

    def has_role(self, role_name):
        """Check if user has a specific role."""
        return self.roles.filter(name=role_name).exists()

    def get_all_permissions(self):
        """Override to include role-based permissions."""
        permissions = set(super().get_all_permissions())
        for role in self.roles.filter(is_active=True):
            role_permissions = role.permissions.values_list('codename', flat=True)
            permissions.update(role_permissions)
        return permissions


class AuditLog(models.Model):
    """Audit logging for user actions."""
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('VIEW', 'View'),
        ('EXPORT', 'Export'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, help_text='Model affected by the action')
    object_id = models.PositiveIntegerField(null=True, blank=True, help_text='ID of the affected object')
    object_repr = models.CharField(max_length=200, blank=True, help_text='String representation of the object')
    changes = models.JSONField(blank=True, null=True, help_text='Changes made (for updates)')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    session_key = models.CharField(max_length=40, blank=True)
    success = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['action', 'timestamp']),
        ]


class UserSession(models.Model):
    """Track user sessions for security and audit purposes."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} session from {self.login_time}"

    class Meta:
        ordering = ['-login_time']

    def logout(self):
        """Mark session as logged out."""
        self.logout_time = timezone.now()
        self.is_active = False
        self.save()

    @property
    def duration(self):
        """Calculate session duration."""
        end_time = self.logout_time or timezone.now()
        return end_time - self.login_time