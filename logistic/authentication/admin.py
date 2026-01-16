from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Role, AuditLog, UserSession


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    filter_horizontal = ['permissions']


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['email', 'username', 'first_name', 'last_name', 'is_active', 'get_primary_role']
    list_filter = ['is_active', 'roles', 'date_joined']
    search_fields = ['email', 'username', 'first_name', 'last_name', 'employee_id']
    ordering = ['email']

    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone', 'employee_id', 'department')}),
        ('Roles', {'fields': ('roles',)}),
    )
    filter_horizontal = ['roles']

    def get_primary_role(self, obj):
        return obj.get_primary_role()
    get_primary_role.short_description = 'Primary Role'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'object_repr', 'timestamp', 'success']
    list_filter = ['action', 'model_name', 'success', 'timestamp']
    search_fields = ['user__email', 'model_name', 'object_repr', 'ip_address']
    ordering = ['-timestamp']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'object_repr',
                      'changes', 'ip_address', 'user_agent', 'timestamp', 'session_key', 'success']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'login_time', 'logout_time', 'is_active', 'duration']
    list_filter = ['is_active', 'login_time']
    search_fields = ['user__email', 'ip_address']
    ordering = ['-login_time']
    readonly_fields = ['user', 'session_key', 'ip_address', 'user_agent', 'login_time', 'logout_time', 'is_active']

    def duration(self, obj):
        return obj.duration if obj.duration else None
    duration.short_description = 'Duration'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(User, CustomUserAdmin)
