from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, TemplateView
)
from django.views.generic.edit import FormView
from django.db.models import Q
from django.utils import timezone
from .models import ASN, ASNItem, ShipmentSchedule, InboundTracking
from vendor_management.models import PurchaseOrder, PurchaseOrderItem


class ASNListView(LoginRequiredMixin, ListView):
    """List all ASNs."""
    model = ASN
    template_name = 'asn_shipment/asn_list.html'
    context_object_name = 'asns'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('vendor', 'purchase_order')
        status = self.request.GET.get('status')
        vendor = self.request.GET.get('vendor')
        search = self.request.GET.get('search')

        if status:
            queryset = queryset.filter(status=status)
        if vendor:
            queryset = queryset.filter(vendor_id=vendor)
        if search:
            queryset = queryset.filter(
                Q(asn_number__icontains=search) |
                Q(vendor__name__icontains=search) |
                Q(purchase_order__po_number__icontains=search)
            )

        return queryset.order_by('-created_at')


class ASNDetailView(LoginRequiredMixin, DetailView):
    """ASN detail view."""
    model = ASN
    template_name = 'asn_shipment/asn_detail.html'
    context_object_name = 'asn'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all().select_related('purchase_order_item')
        context['tracking'] = getattr(self.object, 'tracking', None)
        return context


class ASNCreateView(LoginRequiredMixin, CreateView):
    """Create new ASN."""
    model = ASN
    template_name = 'asn_shipment/asn_form.html'
    fields = ['purchase_order', 'expected_ship_date', 'expected_arrival_date',
             'carrier_name', 'tracking_number', 'vehicle_number', 'driver_name',
             'driver_phone', 'notes', 'special_instructions']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filter to show only approved POs
        form.fields['purchase_order'].queryset = PurchaseOrder.objects.filter(
            status='APPROVED'
        )
        return form

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.vendor = form.instance.purchase_order.vendor
        response = super().form_valid(form)

        # Create ASN items from PO items
        self._create_asn_items(form.instance)

        messages.success(self.request, f'ASN {self.object.asn_number} created successfully.')
        return response

    def _create_asn_items(self, asn):
        """Create ASN items from PO items."""
        for po_item in asn.purchase_order.items.all():
            ASNItem.objects.create(
                asn=asn,
                purchase_order_item=po_item,
                item_code=po_item.item_code,
                item_description=po_item.item_description,
                quantity_expected=po_item.quantity_ordered - po_item.quantity_received,
                unit_price=po_item.unit_price,
            )


class ASNUpdateView(LoginRequiredMixin, UpdateView):
    """Update ASN."""
    model = ASN
    template_name = 'asn_shipment/asn_form.html'
    fields = ['expected_ship_date', 'actual_ship_date', 'expected_arrival_date',
             'actual_arrival_date', 'carrier_name', 'tracking_number', 'vehicle_number',
             'driver_name', 'driver_phone', 'notes', 'special_instructions']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'ASN {self.object.asn_number} updated successfully.')
        return response


class ASNApproveView(LoginRequiredMixin, TemplateView):
    """Approve ASN."""

    def post(self, request, *args, **kwargs):
        asn = get_object_or_404(ASN, pk=kwargs['pk'])

        if asn.status != 'CREATED':
            messages.error(request, 'ASN is not in created status.')
            return redirect('asn_shipment:asn_detail', pk=asn.pk)

        asn.status = 'APPROVED'
        asn.approved_by = request.user
        asn.approved_at = timezone.now()
        asn.save()

        messages.success(request, f'ASN {asn.asn_number} approved successfully.')
        return redirect('asn_shipment:asn_detail', pk=asn.pk)


class ASNStatusUpdateView(LoginRequiredMixin, UpdateView):
    """Update ASN status."""
    model = ASN
    template_name = 'asn_shipment/asn_status_update.html'
    fields = ['status', 'actual_ship_date', 'actual_arrival_date']

    def form_valid(self, form):
        old_status = self.object.status
        response = super().form_valid(form)

        # Create tracking record if status changed to IN_TRANSIT
        if old_status != 'IN_TRANSIT' and self.object.status == 'IN_TRANSIT':
            InboundTracking.objects.get_or_create(
                asn=self.object,
                defaults={'current_location': 'In Transit'}
            )

        messages.success(self.request, f'ASN {self.object.asn_number} status updated.')
        return response


class CreateASNFromPOView(LoginRequiredMixin, TemplateView):
    """Create ASN from existing PO."""

    def get(self, request, *args, **kwargs):
        po = get_object_or_404(PurchaseOrder, pk=kwargs['po_id'])
        return redirect(reverse('asn_shipment:asn_create') + f'?po={po.id}')

    def post(self, request, *args, **kwargs):
        po = get_object_or_404(PurchaseOrder, pk=kwargs['po_id'])

        # Create ASN
        asn = ASN.objects.create(
            purchase_order=po,
            vendor=po.vendor,
            expected_ship_date=timezone.now().date(),
            expected_arrival_date=po.expected_delivery_date or timezone.now().date(),
            created_by=request.user
        )

        # Create ASN items
        for po_item in po.items.all():
            ASNItem.objects.create(
                asn=asn,
                purchase_order_item=po_item,
                item_code=po_item.item_code,
                item_description=po_item.item_description,
                quantity_expected=po_item.quantity_ordered - po_item.quantity_received,
                unit_price=po_item.unit_price,
            )

        messages.success(request, f'ASN {asn.asn_number} created from PO {po.po_number}.')
        return redirect('asn_shipment:asn_detail', pk=asn.pk)


class ShipmentScheduleListView(LoginRequiredMixin, ListView):
    """List shipment schedules."""
    model = ShipmentSchedule
    template_name = 'asn_shipment/schedule_list.html'
    context_object_name = 'schedules'

    def get_queryset(self):
        return super().get_queryset().select_related('vendor').filter(is_active=True)


class ShipmentScheduleCreateView(LoginRequiredMixin, CreateView):
    """Create shipment schedule."""
    model = ShipmentSchedule
    template_name = 'asn_shipment/schedule_form.html'
    fields = ['vendor', 'frequency', 'day_of_week', 'day_of_month',
             'preferred_time_start', 'preferred_time_end', 'default_carrier',
             'default_driver', 'notes']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Schedule for {self.object.vendor.name} created.')
        return response


class ShipmentScheduleUpdateView(LoginRequiredMixin, UpdateView):
    """Update shipment schedule."""
    model = ShipmentSchedule
    template_name = 'asn_shipment/schedule_form.html'
    fields = ['frequency', 'day_of_week', 'day_of_month',
             'preferred_time_start', 'preferred_time_end', 'default_carrier',
             'default_driver', 'notes', 'is_active']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Schedule for {self.object.vendor.name} updated.')
        return response


class InboundTrackingListView(LoginRequiredMixin, ListView):
    """List inbound tracking."""
    model = InboundTracking
    template_name = 'asn_shipment/tracking_list.html'
    context_object_name = 'tracking_records'

    def get_queryset(self):
        return super().get_queryset().select_related('asn__vendor')


class InboundTrackingUpdateView(LoginRequiredMixin, UpdateView):
    """Update inbound tracking."""
    model = InboundTracking
    template_name = 'asn_shipment/tracking_update.html'
    fields = ['current_location', 'latitude', 'longitude', 'estimated_arrival',
             'delay_reason', 'last_contact', 'contact_person']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Tracking updated for ASN {self.object.asn.asn_number}.')
        return response


class ExpectedArrivalsReportView(LoginRequiredMixin, TemplateView):
    """Expected arrivals report."""
    template_name = 'asn_shipment/expected_arrivals_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get ASNs expected to arrive in the next 7 days
        end_date = timezone.now().date() + timezone.timedelta(days=7)
        expected_asns = ASN.objects.filter(
            expected_arrival_date__lte=end_date,
            status__in=['APPROVED', 'IN_TRANSIT']
        ).select_related('vendor', 'purchase_order').order_by('expected_arrival_date')

        context['expected_asns'] = expected_asns
        return context


class DeliveryPerformanceReportView(LoginRequiredMixin, TemplateView):
    """Delivery performance report."""
    template_name = 'asn_shipment/delivery_performance_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get completed ASNs from last 30 days
        start_date = timezone.now().date() - timezone.timedelta(days=30)
        completed_asns = ASN.objects.filter(
            actual_arrival_date__gte=start_date,
            status='RECEIVED'
        ).select_related('vendor')

        # Calculate performance metrics
        on_time = 0
        total = completed_asns.count()

        for asn in completed_asns:
            if asn.actual_arrival_date <= asn.expected_arrival_date:
                on_time += 1

        context['on_time_percentage'] = (on_time / total * 100) if total > 0 else 0
        context['total_deliveries'] = total
        context['completed_asns'] = completed_asns[:20]  # Last 20 deliveries

        return context