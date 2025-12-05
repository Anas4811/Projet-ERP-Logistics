from django.urls import path
from . import views

app_name = 'asn_shipment'

urlpatterns = [
    # ASN management
    path('asns/', views.ASNListView.as_view(), name='asn_list'),
    path('asns/create/', views.ASNCreateView.as_view(), name='asn_create'),
    path('asns/<int:pk>/', views.ASNDetailView.as_view(), name='asn_detail'),
    path('asns/<int:pk>/update/', views.ASNUpdateView.as_view(), name='asn_update'),
    path('asns/<int:pk>/approve/', views.ASNApproveView.as_view(), name='asn_approve'),
    path('asns/<int:pk>/status-update/', views.ASNStatusUpdateView.as_view(), name='asn_status_update'),

    # ASN from PO
    path('purchase-orders/<int:po_id>/create-asn/', views.CreateASNFromPOView.as_view(), name='create_asn_from_po'),

    # Shipment schedules
    path('schedules/', views.ShipmentScheduleListView.as_view(), name='schedule_list'),
    path('schedules/create/', views.ShipmentScheduleCreateView.as_view(), name='schedule_create'),
    path('schedules/<int:pk>/update/', views.ShipmentScheduleUpdateView.as_view(), name='schedule_update'),

    # Tracking
    path('tracking/', views.InboundTrackingListView.as_view(), name='tracking_list'),
    path('tracking/<int:pk>/update/', views.InboundTrackingUpdateView.as_view(), name='tracking_update'),

    # Reports
    path('reports/expected-arrivals/', views.ExpectedArrivalsReportView.as_view(), name='expected_arrivals_report'),
    path('reports/delivery-performance/', views.DeliveryPerformanceReportView.as_view(), name='delivery_performance_report'),
]
