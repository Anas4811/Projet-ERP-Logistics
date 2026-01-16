"""
URL configuration for logistic project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.shortcuts import redirect

def api_redirect(request):
    """Redirect root URL to API."""
    return redirect('/api/order-fulfillment/')

urlpatterns = [
    path("", api_redirect, name="home"),
    path("admin/", admin.site.urls),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/users/", include("users.urls")),
    path("api/products/", include("products.urls")),
    path("api/warehouse/", include("warehouse.urls")),
    path("api/order-fulfillment/", include("order_fulfillment.urls")),
]
