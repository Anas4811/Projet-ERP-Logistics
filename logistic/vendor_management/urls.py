from django.urls import path
from . import views

app_name = 'vendor_management'

urlpatterns = [
    # Vendor management
    path('vendors/', views.VendorListView.as_view(), name='vendor_list'),
    path('vendors/create/', views.VendorCreateView.as_view(), name='vendor_create'),
    path('vendors/<int:pk>/', views.VendorDetailView.as_view(), name='vendor_detail'),
    path('vendors/<int:pk>/update/', views.VendorUpdateView.as_view(), name='vendor_update'),

    # Purchase Orders
    path('purchase-orders/', views.PurchaseOrderListView.as_view(), name='po_list'),
    path('purchase-orders/create/', views.PurchaseOrderCreateView.as_view(), name='po_create'),
    path('purchase-orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='po_detail'),
    path('purchase-orders/<int:pk>/update/', views.PurchaseOrderUpdateView.as_view(), name='po_update'),
    path('purchase-orders/<int:pk>/approve/', views.PurchaseOrderApproveView.as_view(), name='po_approve'),
    path('purchase-orders/<int:pk>/reject/', views.PurchaseOrderRejectView.as_view(), name='po_reject'),

    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notification_list'),
    path('notifications/<int:pk>/mark-read/', views.NotificationMarkReadView.as_view(), name='notification_mark_read'),

    # Analytics/Reports
    path('reports/vendor-performance/', views.VendorPerformanceReportView.as_view(), name='vendor_performance_report'),
    path('reports/po-status/', views.POStatusReportView.as_view(), name='po_status_report'),
]
