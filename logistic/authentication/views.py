from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, TemplateView
)
from django.views.generic.edit import FormView
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from .models import User, Role, AuditLog, UserSession
from .forms import UserCreationForm, UserUpdateForm, RoleForm


class LoginView(DjangoLoginView):
    """Custom login view with audit logging."""
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        """Log successful login."""
        response = super().form_valid(form)

        # Create user session record
        UserSession.objects.create(
            user=self.request.user,
            session_key=self.request.session.session_key,
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

        # Log audit event
        AuditLog.objects.create(
            user=self.request.user,
            action='LOGIN',
            model_name='User',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            session_key=self.request.session.session_key
        )

        return response

    def get_client_ip(self):
        """Get client IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class LogoutView(DjangoLogoutView):
    """Custom logout view with audit logging."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Log logout event
            AuditLog.objects.create(
                user=request.user,
                action='LOGOUT',
                model_name='User',
                session_key=request.session.session_key
            )

            # Update user session
            try:
                session = UserSession.objects.get(
                    user=request.user,
                    session_key=request.session.session_key,
                    is_active=True
                )
                session.logout()
            except UserSession.DoesNotExist:
                pass

        return super().dispatch(request, *args, **kwargs)


class PasswordChangeView(LoginRequiredMixin, FormView):
    """Password change view."""
    template_name = 'authentication/password_change.html'
    success_url = reverse_lazy('authentication:profile')

    def form_valid(self, form):
        # Log password change
        AuditLog.objects.create(
            user=self.request.user,
            action='UPDATE',
            model_name='User',
            object_repr=f"Password changed for {self.request.user}",
            session_key=self.request.session.session_key
        )
        return super().form_valid(form)


class UserListView(LoginRequiredMixin, ListView):
    """List all users."""
    model = User
    template_name = 'authentication/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(roles__name=role)
        return queryset.distinct()


class UserDetailView(LoginRequiredMixin, DetailView):
    """User detail view."""
    model = User
    template_name = 'authentication/user_detail.html'
    context_object_name = 'user_profile'


class UserCreateView(LoginRequiredMixin, CreateView):
    """Create new user."""
    model = User
    form_class = UserCreationForm
    template_name = 'authentication/user_form.html'
    success_url = reverse_lazy('authentication:user_list')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Log user creation
        AuditLog.objects.create(
            user=self.request.user,
            action='CREATE',
            model_name='User',
            object_id=self.object.id,
            object_repr=str(self.object),
            session_key=self.request.session.session_key
        )

        messages.success(self.request, f'User {self.object} created successfully.')
        return response


class UserUpdateView(LoginRequiredMixin, UpdateView):
    """Update user."""
    model = User
    form_class = UserUpdateForm
    template_name = 'authentication/user_form.html'
    success_url = reverse_lazy('authentication:user_list')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Log user update
        AuditLog.objects.create(
            user=self.request.user,
            action='UPDATE',
            model_name='User',
            object_id=self.object.id,
            object_repr=str(self.object),
            session_key=self.request.session.session_key
        )

        messages.success(self.request, f'User {self.object} updated successfully.')
        return response


class RoleListView(LoginRequiredMixin, ListView):
    """List all roles."""
    model = Role
    template_name = 'authentication/role_list.html'
    context_object_name = 'roles'


class RoleDetailView(LoginRequiredMixin, DetailView):
    """Role detail view."""
    model = Role
    template_name = 'authentication/role_detail.html'
    context_object_name = 'role'


class RoleCreateView(LoginRequiredMixin, CreateView):
    """Create new role."""
    model = Role
    form_class = RoleForm
    template_name = 'authentication/role_form.html'
    success_url = reverse_lazy('authentication:role_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Role {self.object} created successfully.')
        return response


class RoleUpdateView(LoginRequiredMixin, UpdateView):
    """Update role."""
    model = Role
    form_class = RoleForm
    template_name = 'authentication/role_form.html'
    success_url = reverse_lazy('authentication:role_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Role {self.object} updated successfully.')
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view."""
    template_name = 'authentication/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['recent_sessions'] = UserSession.objects.filter(
            user=self.request.user
        ).order_by('-login_time')[:10]
        return context


class AuditLogListView(LoginRequiredMixin, ListView):
    """Audit log list view."""
    model = AuditLog
    template_name = 'authentication/audit_log_list.html'
    context_object_name = 'audit_logs'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by user if specified
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by action if specified
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action=action)

        # Filter by date range
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)

        return queryset.order_by('-timestamp')