from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, TemplateView
)
from django.views.generic.edit import FormView
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.http import JsonResponse
from .models import GateQueue, VehicleInspection, DocumentVerification, GateLog
from asn_shipment.models import ASN


class GateQueueListView(LoginRequiredMixin, ListView):
    """List gate queue."""
    model = GateQueue
    template_name = 'gate_checkin/queue_list.html'
    context_object_name = 'queue_items'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('asn__vendor', 'check_in_by')
        status = self.request.GET.get('status')
        search = self.request.GET.get('search')

        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(
                Q(queue_number__icontains=search) |
                Q(vehicle_number__icontains=search) |
                Q(driver_name__icontains=search)
            )

        return queryset.order_by('priority', 'created_at')


class GateQueueDetailView(LoginRequiredMixin, DetailView):
    """Gate queue detail view."""
    model = GateQueue
    template_name = 'gate_checkin/queue_detail.html'
    context_object_name = 'queue_item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['inspections'] = self.object.inspections.all()
        context['documents'] = self.object.documents.all()
        context['logs'] = self.object.logs.all().order_by('-timestamp')
        return context


class GateQueueCreateView(LoginRequiredMixin, CreateView):
    """Create new gate queue entry."""
    model = GateQueue
    template_name = 'gate_checkin/queue_form.html'
    fields = ['asn', 'vehicle_number', 'trailer_number', 'driver_name',
             'driver_id', 'driver_phone', 'driver_license']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filter to show only ASNs that are expected to arrive
        form.fields['asn'].queryset = ASN.objects.filter(
            status__in=['APPROVED', 'IN_TRANSIT'],
            expected_arrival_date__gte=timezone.now().date()
        ).select_related('vendor')
        return form

    def form_valid(self, form):
        response = super().form_valid(form)

        # Log queue creation
        GateLog.objects.create(
            gate_queue=self.object,
            activity='ARRIVAL',
            performed_by=self.request.user,
            description=f'Vehicle {self.object.vehicle_number} arrived at gate.'
        )

        messages.success(self.request, f'Queue entry {self.object.queue_number} created.')
        return response


class GateCheckInView(LoginRequiredMixin, UpdateView):
    """Check-in vehicle at gate."""
    model = GateQueue
    template_name = 'gate_checkin/check_in_form.html'
    fields = ['check_in_notes']

    def form_valid(self, form):
        self.object.status = 'CHECKING_IN'
        self.object.check_in_time = timezone.now()
        self.object.check_in_by = self.request.user
        response = super().form_valid(form)

        # Log check-in
        GateLog.objects.create(
            gate_queue=self.object,
            activity='CHECK_IN_START',
            performed_by=self.request.user,
            description='Check-in process started.'
        )

        messages.success(self.request, f'Vehicle {self.object.vehicle_number} checked in.')
        return response


class GateVerificationView(LoginRequiredMixin, TemplateView):
    """Verify documents and vehicle."""
    template_name = 'gate_checkin/verification_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['queue_item'] = get_object_or_404(GateQueue, pk=kwargs['pk'])
        return context

    def post(self, request, *args, **kwargs):
        queue_item = get_object_or_404(GateQueue, pk=kwargs['pk'])

        # Update verification status
        queue_item.status = 'VERIFIED'
        queue_item.verification_time = timezone.now()
        queue_item.verification_by = request.user
        queue_item.documents_verified = request.POST.get('documents_verified') == 'on'
        queue_item.vehicle_inspection_passed = request.POST.get('vehicle_inspection_passed') == 'on'
        queue_item.cargo_inspection_passed = request.POST.get('cargo_inspection_passed') == 'on'
        queue_item.verification_notes = request.POST.get('verification_notes', '')
        queue_item.save()

        # Log verification
        GateLog.objects.create(
            gate_queue=queue_item,
            activity='APPROVAL',
            performed_by=request.user,
            description='Document and vehicle verification completed.'
        )

        messages.success(request, f'Verification completed for {queue_item.queue_number}.')
        return redirect('gate_checkin:queue_detail', pk=queue_item.pk)


class GateCompleteView(LoginRequiredMixin, UpdateView):
    """Complete gate check-in process."""
    model = GateQueue
    template_name = 'gate_checkin/complete_form.html'
    fields = []

    def form_valid(self, form):
        self.object.status = 'COMPLETED'
        self.object.actual_completion_time = timezone.now()
        response = super().form_valid(form)

        # Update ASN status if applicable
        if self.object.asn.status == 'IN_TRANSIT':
            self.object.asn.status = 'ARRIVED'
            self.object.asn.actual_arrival_date = timezone.now().date()
            self.object.asn.save()

        # Log completion
        GateLog.objects.create(
            gate_queue=self.object,
            activity='DEPARTURE',
            performed_by=self.request.user,
            description='Gate check-in process completed.'
        )

        messages.success(self.request, f'Gate check-in completed for {self.object.queue_number}.')
        return response


class VehicleInspectionListView(LoginRequiredMixin, ListView):
    """List vehicle inspections."""
    model = VehicleInspection
    template_name = 'gate_checkin/inspection_list.html'
    context_object_name = 'inspections'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('gate_queue', 'inspected_by')
        queue_id = self.request.GET.get('queue')
        if queue_id:
            queryset = queryset.filter(gate_queue_id=queue_id)
        return queryset.order_by('-inspected_at')


class VehicleInspectionCreateView(LoginRequiredMixin, CreateView):
    """Create vehicle inspection."""
    model = VehicleInspection
    template_name = 'gate_checkin/inspection_form.html'
    fields = ['inspection_type', 'exterior_condition', 'interior_condition',
             'tire_condition', 'brake_condition', 'lights_condition',
             'fire_extinguisher', 'first_aid_kit', 'warning_triangles',
             'spare_tire', 'passed_inspection', 'critical_issues',
             'recommended_actions', 'inspection_notes']

    def form_valid(self, form):
        form.instance.gate_queue_id = self.kwargs['queue_id']
        form.instance.inspected_by = self.request.user
        response = super().form_valid(form)

        # Log inspection
        GateLog.objects.create(
            gate_queue=self.object.gate_queue,
            activity='VEHICLE_INSPECTION',
            performed_by=self.request.user,
            description=f'{self.object.inspection_type} inspection completed.'
        )

        messages.success(self.request, 'Vehicle inspection recorded.')
        return response


class DocumentVerificationView(LoginRequiredMixin, TemplateView):
    """Document verification form."""
    template_name = 'gate_checkin/document_verification.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['queue_item'] = get_object_or_404(GateQueue, pk=kwargs['queue_id'])
        context['documents'] = context['queue_item'].documents.all()
        return context

    def post(self, request, *args, **kwargs):
        queue_item = get_object_or_404(GateQueue, pk=kwargs['queue_id'])

        # Process document verifications
        doc_types = request.POST.getlist('document_type[]')
        doc_present = request.POST.getlist('is_present[]')
        doc_valid = request.POST.getlist('is_valid[]')
        doc_notes = request.POST.getlist('verification_notes[]')

        for i, doc_type in enumerate(doc_types):
            DocumentVerification.objects.create(
                gate_queue=queue_item,
                document_type=doc_type,
                is_present=doc_present[i] == 'on' if i < len(doc_present) else False,
                is_valid=doc_valid[i] == 'on' if i < len(doc_valid) else False,
                verified_by=request.user,
                verification_notes=doc_notes[i] if i < len(doc_notes) else ''
            )

        # Log document verification
        GateLog.objects.create(
            gate_queue=queue_item,
            activity='DOCUMENT_VERIFICATION',
            performed_by=request.user,
            description='Document verification completed.'
        )

        messages.success(request, 'Document verification completed.')
        return redirect('gate_checkin:queue_detail', pk=queue_item.pk)


class DocumentVerificationListView(LoginRequiredMixin, ListView):
    """List document verifications."""
    model = DocumentVerification
    template_name = 'gate_checkin/document_list.html'
    context_object_name = 'documents'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('gate_queue', 'verified_by')
        queue_id = self.request.GET.get('queue')
        doc_type = self.request.GET.get('type')
        if queue_id:
            queryset = queryset.filter(gate_queue_id=queue_id)
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)
        return queryset.order_by('-verified_at')


class GateLogListView(LoginRequiredMixin, ListView):
    """List gate activity logs."""
    model = GateLog
    template_name = 'gate_checkin/log_list.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset().select_related('gate_queue', 'performed_by')
        queue_id = self.request.GET.get('queue')
        activity = self.request.GET.get('activity')
        if queue_id:
            queryset = queryset.filter(gate_queue_id=queue_id)
        if activity:
            queryset = queryset.filter(activity=activity)
        return queryset.order_by('-timestamp')


class GateLogDetailView(LoginRequiredMixin, DetailView):
    """Gate log detail view."""
    model = GateLog
    template_name = 'gate_checkin/log_detail.html'
    context_object_name = 'log'


class GateDashboardView(LoginRequiredMixin, TemplateView):
    """Gate dashboard with real-time status."""
    template_name = 'gate_checkin/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Current queue status
        context['waiting_count'] = GateQueue.objects.filter(status='WAITING').count()
        context['checking_count'] = GateQueue.objects.filter(status='CHECKING_IN').count()
        context['verified_count'] = GateQueue.objects.filter(status='VERIFIED').count()
        context['completed_today'] = GateQueue.objects.filter(
            status='COMPLETED',
            created_at__date=timezone.now().date()
        ).count()

        # Recent activity
        context['recent_queue'] = GateQueue.objects.select_related(
            'asn__vendor'
        ).order_by('-created_at')[:10]

        return context


class QueuePerformanceReportView(LoginRequiredMixin, TemplateView):
    """Queue performance report."""
    template_name = 'gate_checkin/queue_performance_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Performance metrics for last 30 days
        start_date = timezone.now() - timezone.timedelta(days=30)
        completed_queues = GateQueue.objects.filter(
            actual_completion_time__gte=start_date,
            status='COMPLETED'
        )

        if completed_queues.exists():
            avg_wait_time = completed_queues.aggregate(
                avg_time=Avg('actual_completion_time') - Avg('check_in_time')
            )['avg_time']
            context['avg_processing_time'] = avg_wait_time

        context['total_processed'] = completed_queues.count()
        context['avg_daily_processed'] = completed_queues.count() / 30

        return context


class DailyActivityReportView(LoginRequiredMixin, TemplateView):
    """Daily activity report."""
    template_name = 'gate_checkin/daily_activity_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()
        context['today_queues'] = GateQueue.objects.filter(
            created_at__date=today
        ).select_related('asn__vendor', 'check_in_by')

        context['today_logs'] = GateLog.objects.filter(
            timestamp__date=today
        ).select_related('gate_queue', 'performed_by').order_by('-timestamp')[:50]

        return context


# API Views for real-time updates
class QueueStatusAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint for queue status."""

    def get(self, request, *args, **kwargs):
        status_counts = GateQueue.objects.values('status').annotate(
            count=Count('status')
        )

        data = {item['status']: item['count'] for item in status_counts}
        return JsonResponse(data)


class QueuePositionAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint for queue position."""

    def get(self, request, *args, **kwargs):
        queue_item = get_object_or_404(GateQueue, pk=kwargs['pk'])

        # Calculate position in queue
        position = GateQueue.objects.filter(
            status='WAITING',
            created_at__lt=queue_item.created_at
        ).count() + 1

        data = {
            'position': position,
            'status': queue_item.status,
            'estimated_wait': None  # Could implement wait time estimation
        }
        return JsonResponse(data)