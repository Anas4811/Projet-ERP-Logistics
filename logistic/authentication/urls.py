from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # Authentication views
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('password-change/', views.PasswordChangeView.as_view(), name='password_change'),

    # User management
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),

    # Role management
    path('roles/', views.RoleListView.as_view(), name='role_list'),
    path('roles/create/', views.RoleCreateView.as_view(), name='role_create'),
    path('roles/<int:pk>/', views.RoleDetailView.as_view(), name='role_detail'),
    path('roles/<int:pk>/update/', views.RoleUpdateView.as_view(), name='role_update'),

    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),

    # Audit logs
    path('audit-logs/', views.AuditLogListView.as_view(), name='audit_log_list'),
]
