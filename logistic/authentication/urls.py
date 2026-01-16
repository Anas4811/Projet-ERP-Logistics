from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, api_views

app_name = 'authentication'

# Web interface URLs
web_urlpatterns = [
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

# API URLs
api_urlpatterns = [
    path('token/', api_views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('register/', api_views.register, name='register'),
    path('logout/', api_views.logout, name='logout'),
    path('profile/', api_views.profile, name='profile'),
]

urlpatterns = web_urlpatterns + api_urlpatterns
