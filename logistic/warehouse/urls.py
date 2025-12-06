from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StorageLocationViewSet,
    PutawayRuleViewSet,
    StockItemViewSet,
    StockMovementViewSet,
)

router = DefaultRouter()
router.register(r"locations", StorageLocationViewSet, basename="storagelocation")
router.register(r"putaway-rules", PutawayRuleViewSet, basename="putawayrule")
router.register(r"stock-items", StockItemViewSet, basename="stockitem")
router.register(r"movements", StockMovementViewSet, basename="stockmovement")

urlpatterns = [
    path("", include(router.urls)),
]

