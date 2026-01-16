from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission
from .models import User, Role, AuditLog, UserSession


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Django permissions."""
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for roles."""
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions', 'permission_ids', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        permission_ids = validated_data.pop('permission_ids', [])
        role = super().create(validated_data)
        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids)
            role.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        permission_ids = validated_data.pop('permission_ids', [])
        role = super().update(instance, validated_data)
        if permission_ids is not None:
            permissions = Permission.objects.filter(id__in=permission_ids)
            role.permissions.set(permissions)
        return role


class UserSerializer(serializers.ModelSerializer):
    """Serializer for users."""
    roles = RoleSerializer(many=True, read_only=True)
    role_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    full_name = serializers.CharField(read_only=True)
    primary_role = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'phone', 'employee_id', 'department', 'roles', 'role_ids',
            'primary_role', 'is_active', 'date_joined', 'last_login'
        ]
        read_only_fields = ['date_joined', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        role_ids = validated_data.pop('role_ids', [])
        password = validated_data.pop('password')
        user = super().create(validated_data)
        user.set_password(password)
        user.save()

        if role_ids:
            roles = Role.objects.filter(id__in=role_ids, is_active=True)
            user.roles.set(roles)

        return user

    def update(self, instance, validated_data):
        role_ids = validated_data.pop('role_ids', [])
        password = validated_data.pop('password', None)

        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        if role_ids is not None:
            roles = Role.objects.filter(id__in=role_ids, is_active=True)
            user.roles.set(roles)

        return user


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating users."""
    password = serializers.CharField(write_only=True)
    role_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name', 'password',
            'phone', 'employee_id', 'department', 'role_ids'
        ]

    def create(self, validated_data):
        role_ids = validated_data.pop('role_ids', [])
        user = super().create(validated_data)
        if role_ids:
            roles = Role.objects.filter(id__in=role_ids, is_active=True)
            user.roles.set(roles)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            if user:
                if user.is_active:
                    data['user'] = user
                else:
                    raise serializers.ValidationError('User account is disabled.')
            else:
                raise serializers.ValidationError('Unable to log in with provided credentials.')
        else:
            raise serializers.ValidationError('Must include email and password.')

        return data


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords don't match.")
        return data


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_email', 'user_full_name', 'action', 'model_name',
            'object_id', 'object_repr', 'changes', 'ip_address', 'user_agent',
            'timestamp', 'session_key', 'success'
        ]
        read_only_fields = ['timestamp']


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for user sessions."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    duration = serializers.CharField(read_only=True)

    class Meta:
        model = UserSession
        fields = [
            'id', 'user', 'user_email', 'session_key', 'ip_address',
            'user_agent', 'login_time', 'logout_time', 'is_active', 'duration'
        ]
        read_only_fields = ['login_time', 'logout_time', 'duration']


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""
    roles = RoleSerializer(many=True, read_only=True)
    recent_sessions = UserSessionSerializer(many=True, read_only=True, source='sessions')

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'phone',
            'employee_id', 'department', 'roles', 'is_active', 'date_joined',
            'last_login', 'recent_sessions'
        ]
        read_only_fields = ['date_joined', 'last_login']
