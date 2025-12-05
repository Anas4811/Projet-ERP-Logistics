from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, TemplateView
)
from django.views.generic.edit import FormView
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from .models import Vendor, PurchaseOrder, PurchaseOrderItem, Notification


class VendorListView(LoginRequiredMixin, ListView):
    """List all vendors."""
    model = Vendor
    template_name = 'vendor_management/vendor_list.html'
    context_object_name = 'vendors'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(vendor_code__icontains=search) |
                Q(email__icontains=search)
            )

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('name')


class VendorDetailView(LoginRequiredMixin, DetailView):
    """Vendor detail view."""
    model = Vendor
    template_name = 'vendor_management/vendor_detail.html'
    context_object_name = 'vendor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add recent POs, performance metrics, etc.
        context['recent_pos'] = self.object.purchase_orders.order_by('-created_at')[:10]
        context['active_pos'] = self.object.purchase_orders.filter(
            status__in=['APPROVED', 'ORDERED', 'PARTIALLY_RECEIVED']
        ).count()
        return context


class VendorCreateView(LoginRequiredMixin, CreateView):
    """Create new vendor."""
    model = Vendor
    template_name = 'vendor_management/vendor_form.html'
    fields = ['name', 'vendor_code', 'contact_person', 'email', 'phone',
             'address', 'city', 'state', 'country', 'postal_code',
             'tax_id', 'registration_number', 'payment_terms', 'status']

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Vendor {self.object.name} created successfully.')
        return response


class VendorUpdateView(LoginRequiredMixin, UpdateView):
    """Update vendor."""
    model = Vendor
    template_name = 'vendor_management/vendor_form.html'
    fields = ['name', 'vendor_code', 'contact_person', 'email', 'phone',
             'address', 'city', 'state', 'country', 'postal_code',
             'tax_id', 'registration_number', 'payment_terms', 'status',
             'is_preferred']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Vendor {self.object.name} updated successfully.')
        return response


class PurchaseOrderListView(LoginRequiredMixin, ListView):
    """List all purchase orders."""
    model = PurchaseOrder
    template_name = 'vendor_management/po_list.html'
    context_object_name = 'purchase_orders'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.GET.get('status')
        vendor = self.request.GET.get('vendor')
        search = self.request.GET.get('search')

        if status:
            queryset = queryset.filter(status=status)
        if vendor:
            queryset = queryset.filter(vendor_id=vendor)
        if search:
            queryset = queryset.filter(
                Q(po_number__icontains=search) |
                Q(vendor__name__icontains=search)
            )

        return queryset.select_related('vendor', 'created_by')


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    """Purchase order detail view."""
    model = PurchaseOrder
    template_name = 'vendor_management/po_detail.html'
    context_object_name = 'po'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all()
        return context


class PurchaseOrderCreateView(LoginRequiredMixin, CreateView):
    """Create new purchase order."""
    model = PurchaseOrder
    template_name = 'vendor_management/po_form.html'
    fields = ['vendor', 'order_date', 'expected_delivery_date', 'priority',
             'shipping_address', 'special_instructions', 'internal_notes']

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Purchase Order {self.object.po_number} created successfully.')
        return response


class PurchaseOrderUpdateView(LoginRequiredMixin, UpdateView):
    """Update purchase order."""
    model = PurchaseOrder
    template_name = 'vendor_management/po_form.html'
    fields = ['vendor', 'order_date', 'expected_delivery_date', 'priority',
             'shipping_address', 'special_instructions', 'internal_notes']

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Purchase Order {self.object.po_number} updated successfully.')
        return response


class PurchaseOrderApproveView(LoginRequiredMixin, TemplateView):
    """Approve purchase order."""

    def post(self, request, *args, **kwargs):
        po = get_object_or_404(PurchaseOrder, pk=kwargs['pk'])

        if po.status != 'PENDING_APPROVAL':
            messages.error(request, 'PO is not pending approval.')
            return redirect('vendor_management:po_detail', pk=po.pk)

        po.status = 'APPROVED'
        po.approved_by = request.user
        po.approved_at = timezone.now()
        po.save()

        # Create notification
        Notification.objects.create(
            recipient=po.created_by,
            notification_type='PO_APPROVAL',
            title=f'PO {po.po_number} Approved',
            message=f'Your purchase order {po.po_number} has been approved.',
            related_po=po
        )

        messages.success(request, f'Purchase Order {po.po_number} approved successfully.')
        return redirect('vendor_management:po_detail', pk=po.pk)


class PurchaseOrderRejectView(LoginRequiredMixin, FormView):
    """Reject purchase order."""
    template_name = 'vendor_management/po_reject.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['po'] = get_object_or_404(PurchaseOrder, pk=self.kwargs['pk'])
        return context

    def form_valid(self, form):
        po = get_object_or_404(PurchaseOrder, pk=self.kwargs['pk'])
        rejection_reason = form.cleaned_data.get('rejection_reason', '')

        po.status = 'REJECTED'
        po.approval_notes = rejection_reason
        po.approved_by = self.request.user
        po.approved_at = timezone.now()
        po.save()

        # Create notification
        Notification.objects.create(
            recipient=po.created_by,
            notification_type='PO_APPROVAL',
            title=f'PO {po.po_number} Rejected',
            message=f'Your purchase order {po.po_number} has been rejected. Reason: {rejection_reason}',
            related_po=po
        )

        messages.success(self.request, f'Purchase Order {po.po_number} rejected.')
        return redirect('vendor_management:po_detail', pk=po.pk)


class NotificationListView(LoginRequiredMixin, ListView):
    """List user notifications."""
    model = Notification
    template_name = 'vendor_management/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().filter(
            recipient=self.request.user
        ).order_by('-created_at')


class NotificationMarkReadView(LoginRequiredMixin, TemplateView):
    """Mark notification as read."""

    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(
            Notification,
            pk=kwargs['pk'],
            recipient=request.user
        )
        notification.mark_as_read()
        return redirect('vendor_management:notification_list')


class VendorPerformanceReportView(LoginRequiredMixin, TemplateView):
    """Vendor performance report."""
    template_name = 'vendor_management/vendor_performance_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get vendor performance data
        vendors = Vendor.objects.annotate(
            total_pos=Count('purchase_orders'),
            on_time_deliveries=Count('purchase_orders', filter=Q(
                purchase_orders__actual_delivery_date__lte=models.F('purchase_orders__expected_delivery_date')
            )),
            avg_rating=Avg('rating')
        ).filter(total_pos__gt=0)

        context['vendors'] = vendors
        return context


class POStatusReportView(LoginRequiredMixin, TemplateView):
    """Purchase order status report."""
    template_name = 'vendor_management/po_status_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # PO status summary
        status_counts = PurchaseOrder.objects.values('status').annotate(
            count=Count('status')
        ).order_by('status')

        context['status_counts'] = status_counts

        # Overdue POs
        overdue_pos = PurchaseOrder.objects.filter(
            expected_delivery_date__lt=timezone.now().date(),
            status__in=['APPROVED', 'ORDERED', 'PARTIALLY_RECEIVED']
        ).select_related('vendor')

        context['overdue_pos'] = overdue_pos
        return context