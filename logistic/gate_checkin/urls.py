from django.urls import path
from . import views

app_name = 'gate_checkin'

urlpatterns = [
    # Gate queue management
    path('queue/', views.GateQueueListView.as_view(), name='queue_list'),
    path('queue/create/', views.GateQueueCreateView.as_view(), name='queue_create'),
    path('queue/<int:pk>/', views.GateQueueDetailView.as_view(), name='queue_detail'),
    path('queue/<int:pk>/check-in/', views.GateCheckInView.as_view(), name='queue_check_in'),
    path('queue/<int:pk>/verify/', views.GateVerificationView.as_view(), name='queue_verify'),
    path('queue/<int:pk>/complete/', views.GateCompleteView.as_view(), name='queue_complete'),

    # Vehicle inspections
    path('inspections/', views.VehicleInspectionListView.as_view(), name='inspection_list'),
    path('queue/<int:queue_id>/inspection/', views.VehicleInspectionCreateView.as_view(), name='inspection_create'),

    # Document verification
    path('documents/', views.DocumentVerificationListView.as_view(), name='document_list'),
    path('queue/<int:queue_id>/documents/', views.DocumentVerificationView.as_view(), name='document_verification'),

    # Gate logs
    path('logs/', views.GateLogListView.as_view(), name='log_list'),
    path('logs/<int:pk>/', views.GateLogDetailView.as_view(), name='log_detail'),

    # Dashboard and reports
    path('dashboard/', views.GateDashboardView.as_view(), name='dashboard'),
    path('reports/queue-performance/', views.QueuePerformanceReportView.as_view(), name='queue_performance_report'),
    path('reports/daily-activity/', views.DailyActivityReportView.as_view(), name='daily_activity_report'),

    # API endpoints for real-time updates
    path('api/queue-status/', views.QueueStatusAPIView.as_view(), name='api_queue_status'),
    path('api/queue-position/<int:pk>/', views.QueuePositionAPIView.as_view(), name='api_queue_position'),
]
