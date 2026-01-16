from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import (
    AisleViewSet,
    BinViewSet,
    OutboundOrderLineViewSet,
    OutboundOrderViewSet,
    PickConfirmationViewSet,
    ProductViewSet,
    PutawayRuleViewSet,
    RackViewSet,
    StockItemViewSet,
    StockMovementViewSet,
    WarehouseViewSet,
    ZoneViewSet,
)

router = DefaultRouter()
router.register(r'warehouses', WarehouseViewSet)
router.register(r'zones', ZoneViewSet)
router.register(r'aisles', AisleViewSet)
router.register(r'racks', RackViewSet)
router.register(r'bins', BinViewSet)
router.register(r'products', ProductViewSet)
router.register(r'stock-items', StockItemViewSet)
router.register(r'putaway-rules', PutawayRuleViewSet)
router.register(r'movements', StockMovementViewSet)
router.register(r'outbound-orders', OutboundOrderViewSet)
router.register(r'outbound-order-lines', OutboundOrderLineViewSet)
router.register(r'pick-confirmations', PickConfirmationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
