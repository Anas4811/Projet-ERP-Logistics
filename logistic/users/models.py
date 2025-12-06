from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("warehouse_manager", "Warehouse Manager"),
        ("worker", "Worker"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="worker")
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_warehouse_manager(self):
        return self.role == "warehouse_manager"

    @property
    def is_worker(self):
        return self.role == "worker"

