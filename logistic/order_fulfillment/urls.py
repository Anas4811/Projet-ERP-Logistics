"""
URL configuration for Order Fulfillment & Distribution.

Provides API endpoints for order management, picking, packing, and shipping.
"""

from rest_framework.routers import DefaultRouter

from .views import OrderViewSet, PickingViewSet, PackingViewSet, ShipmentViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'picking', PickingViewSet, basename='picking')
router.register(r'packing', PackingViewSet, basename='packing')
router.register(r'shipments', ShipmentViewSet, basename='shipment')

# URL patterns
urlpatterns = router.urls
