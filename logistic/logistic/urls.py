"""
URL configuration for logistic project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Import API ViewSets
from authentication.api_views import (
    UserViewSet, RoleViewSet, PermissionViewSet,
    AuditLogViewSet, UserSessionViewSet
)
from vendor_management.api_views import (
    VendorViewSet, VendorContactViewSet, PurchaseOrderViewSet,
    PurchaseOrderItemViewSet, NotificationViewSet
)
from asn_shipment.api_views import (
    ASNViewSet, ASNItemViewSet, ShipmentScheduleViewSet, InboundTrackingViewSet
)
from gate_checkin.api_views import (
    GateQueueViewSet, VehicleInspectionViewSet, DocumentVerificationViewSet, GateLogViewSet
)

def home_redirect(request):
    """Redirect root URL to gate dashboard."""
    return redirect('gate_checkin:dashboard')

# Create API root view using DRF's built-in functionality
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["GET"])
def api_root(request):
    """API root view with available endpoints."""
    return JsonResponse({
        'message': 'ERP Logistics API',
        'version': '1.0.0',
        'endpoints': {
            'authentication': {
                'token': '/api/auth/token/',
                'token_refresh': '/api/auth/token/refresh/',
                'users': '/api/auth/users/',
                'roles': '/api/auth/roles/',
                'permissions': '/api/auth/permissions/',
                'audit_logs': '/api/auth/audit-logs/',
                'sessions': '/api/auth/sessions/'
            },
            'vendor_management': {
                'vendors': '/api/vendors/',
                'purchase_orders': '/api/purchase-orders/',
                'notifications': '/api/notifications/'
            },
            'asn_shipment': {
                'asns': '/api/asns/',
                'shipment_schedules': '/api/shipment-schedules/',
                'inbound_tracking': '/api/inbound-tracking/'
            },
            'gate_checkin': {
                'gate_queue': '/api/gate-queue/',
                'vehicle_inspections': '/api/vehicle-inspections/',
                'document_verifications': '/api/document-verifications/',
                'gate_logs': '/api/gate-logs/'
            },
            'documentation': '/api/docs/'
        }
    })

# Create API router
router = DefaultRouter()

# Authentication API
router.register(r'auth/users', UserViewSet, basename='api-users')
router.register(r'auth/roles', RoleViewSet, basename='api-roles')
router.register(r'auth/permissions', PermissionViewSet, basename='api-permissions')
router.register(r'auth/audit-logs', AuditLogViewSet, basename='api-audit-logs')
router.register(r'auth/sessions', UserSessionViewSet, basename='api-sessions')

# Vendor Management API
router.register(r'vendors', VendorViewSet, basename='api-vendors')
router.register(r'vendors/(?P<vendor_pk>\d+)/contacts', VendorContactViewSet, basename='api-vendor-contacts')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='api-pos')
router.register(r'purchase-orders/(?P<po_pk>\d+)/items', PurchaseOrderItemViewSet, basename='api-po-items')
router.register(r'notifications', NotificationViewSet, basename='api-notifications')

# ASN Shipment API
router.register(r'asns', ASNViewSet, basename='api-asns')
router.register(r'asns/(?P<asn_pk>\d+)/items', ASNItemViewSet, basename='api-asn-items')
router.register(r'shipment-schedules', ShipmentScheduleViewSet, basename='api-schedules')
router.register(r'inbound-tracking', InboundTrackingViewSet, basename='api-tracking')

# Gate Check-in API
router.register(r'gate-queue', GateQueueViewSet, basename='api-gate-queue')
router.register(r'vehicle-inspections', VehicleInspectionViewSet, basename='api-inspections')
router.register(r'document-verifications', DocumentVerificationViewSet, basename='api-documents')
router.register(r'gate-logs', GateLogViewSet, basename='api-gate-logs')

urlpatterns = [
    # Web interface
    path("", home_redirect, name="home"),
    path("admin/", admin.site.urls),
    path("auth/", include("authentication.urls")),
    path("vendor/", include("vendor_management.urls")),
    path("asn/", include("asn_shipment.urls")),
    path("gate/", include("gate_checkin.urls")),

    # API endpoints
    path('api/', api_root, name='api-root'),  # Exact match for /api/ (must be first)
    path('api/', include(router.urls)),
    path('api/auth/token/', include('authentication.urls')),  # Custom token endpoints
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # API documentation
    path('api/docs/', include('rest_framework.urls')),
]
