from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Aisle,
    Bin,
    OutboundOrder,
    OutboundOrderLine,
    PickConfirmation,
    Product,
    PutawayRule,
    Rack,
    StockItem,
    StockMovement,
    Warehouse,
    Zone,
)
from .serializers import (
    AisleSerializer,
    BinSerializer,
    OutboundOrderLineSerializer,
    OutboundOrderSerializer,
    PickConfirmationSerializer,
    ProductSerializer,
    PutawayRuleSerializer,
    RackSerializer,
    StockItemSerializer,
    StockMovementSerializer,
    WarehouseSerializer,
    ZoneSerializer,
)


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by('name')
    serializer_class = WarehouseSerializer


class ZoneViewSet(viewsets.ModelViewSet):
    queryset = Zone.objects.select_related('warehouse').all().order_by('warehouse__name', 'name')
    serializer_class = ZoneSerializer


class AisleViewSet(viewsets.ModelViewSet):
    queryset = Aisle.objects.select_related('zone', 'zone__warehouse').all().order_by('zone__name', 'name')
    serializer_class = AisleSerializer


class RackViewSet(viewsets.ModelViewSet):
    queryset = Rack.objects.select_related('aisle', 'aisle__zone', 'aisle__zone__warehouse').all().order_by('name')
    serializer_class = RackSerializer


class BinViewSet(viewsets.ModelViewSet):
    queryset = Bin.objects.select_related('rack', 'rack__aisle', 'rack__aisle__zone', 'rack__aisle__zone__warehouse').all()
    serializer_class = BinSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('sku')
    serializer_class = ProductSerializer


class StockItemViewSet(viewsets.ModelViewSet):
    queryset = StockItem.objects.select_related(
        'bin',
        'bin__rack',
        'bin__rack__aisle',
        'bin__rack__aisle__zone',
        'bin__rack__aisle__zone__warehouse',
        'product',
    ).all()
    serializer_class = StockItemSerializer

    @action(detail=False, methods=['get'], url_path='report/stock-per-warehouse')
    def report_stock_per_warehouse(self, request):
        rows = (
            StockItem.objects.values(
                'bin__rack__aisle__zone__warehouse_id',
                'bin__rack__aisle__zone__warehouse__name',
            )
            .annotate(total_qty=Sum('quantity'))
            .order_by('bin__rack__aisle__zone__warehouse__name')
        )

        return Response(
            [
                {
                    'warehouse': r['bin__rack__aisle__zone__warehouse_id'],
                    'warehouse_name': r['bin__rack__aisle__zone__warehouse__name'],
                    'total_qty': str(r['total_qty'] or Decimal('0')),
                }
                for r in rows
            ]
        )

    @action(detail=False, methods=['get'], url_path='report/inventory-aging')
    def report_inventory_aging(self, request):
        today = timezone.now().date()
        buckets = {
            '0-30': Decimal('0'),
            '31-90': Decimal('0'),
            '91-180': Decimal('0'),
            '181+': Decimal('0'),
        }

        qs = StockItem.objects.filter(quantity__gt=0).only('quantity', 'created_at')
        for s in qs:
            age_days = (today - s.created_at.date()).days
            if age_days <= 30:
                key = '0-30'
            elif age_days <= 90:
                key = '31-90'
            elif age_days <= 180:
                key = '91-180'
            else:
                key = '181+'
            buckets[key] += s.quantity

        return Response({k: str(v) for k, v in buckets.items()})


class PutawayRuleViewSet(viewsets.ModelViewSet):
    queryset = PutawayRule.objects.select_related('zone', 'zone__warehouse', 'product').all()
    serializer_class = PutawayRuleSerializer


class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.select_related('product', 'from_bin', 'to_bin').all().order_by('-created_at')
    serializer_class = StockMovementSerializer

    @action(detail=False, methods=['get'], url_path='report/fast-slow-moving')
    def report_fast_slow_moving(self, request):
        days = int(request.query_params.get('days', '30'))
        top = int(request.query_params.get('top', '20'))

        if days <= 0:
            return Response({'detail': 'days must be > 0'}, status=status.HTTP_400_BAD_REQUEST)
        if top <= 0:
            return Response({'detail': 'top must be > 0'}, status=status.HTTP_400_BAD_REQUEST)

        since = timezone.now() - timedelta(days=days)
        qs = (
            StockMovement.objects.filter(created_at__gte=since)
            .values('product_id', 'product__sku', 'product__name')
            .annotate(total_qty=Sum('quantity'))
            .order_by('-total_qty')
        )

        rows = list(qs)
        fast = [
            {
                'product': r['product_id'],
                'sku': r['product__sku'],
                'name': r['product__name'],
                'moved_qty': str(r['total_qty'] or Decimal('0')),
            }
            for r in rows[:top]
        ]
        slow = [
            {
                'product': r['product_id'],
                'sku': r['product__sku'],
                'name': r['product__name'],
                'moved_qty': str(r['total_qty'] or Decimal('0')),
            }
            for r in reversed(rows[-top:])
        ]

        return Response({'days': days, 'fast_moving': fast, 'slow_moving': slow})

    @action(detail=False, methods=['post'], url_path='putaway-suggest')
    def putaway_suggest(self, request):
        product_id = request.data.get('product')
        qty_raw = request.data.get('quantity')
        warehouse_id = request.data.get('warehouse')

        if not product_id or qty_raw is None:
            return Response({'detail': 'product and quantity are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            qty = Decimal(str(qty_raw))
        except Exception:
            return Response({'detail': 'Invalid quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        if qty <= 0:
            return Response({'detail': 'Quantity must be > 0.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({'detail': 'Invalid product.'}, status=status.HTTP_400_BAD_REQUEST)

        rule_qs = PutawayRule.objects.select_related('zone', 'zone__warehouse').filter(
            Q(product=product)
            | Q(product_category=product.category)
            | (Q(product__isnull=True) & Q(product_category__isnull=True))
        )
        if warehouse_id is not None:
            rule_qs = rule_qs.filter(zone__warehouse_id=warehouse_id)

        rules = list(rule_qs.order_by('priority', 'id'))
        if not rules:
            fallback = PutawayRule.objects.select_related('zone', 'zone__warehouse').all()
            if warehouse_id is not None:
                fallback = fallback.filter(zone__warehouse_id=warehouse_id)
            rules = list(fallback.order_by('priority', 'id')[:50])

        zone_ids = sorted({r.zone_id for r in rules})
        if not zone_ids:
            return Response({'detail': 'No putaway zones available.'}, status=status.HTTP_400_BAD_REQUEST)

        bins_qs = Bin.objects.filter(rack__aisle__zone_id__in=zone_ids).select_related('rack', 'rack__aisle', 'rack__aisle__zone')
        bins_qs = bins_qs.annotate(used_qty=Sum('stock_items__quantity'))

        best = None
        best_free = None
        for b in bins_qs:
            used = b.used_qty or Decimal('0')
            if b.capacity and b.capacity > 0:
                free = b.capacity - used
                if free < qty:
                    continue
            else:
                free = Decimal('999999999')

            if best is None or free > best_free:
                best = b
                best_free = free

        if best is None:
            return Response({'detail': 'No bin has enough free capacity.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'bin': best.id})


class OutboundOrderViewSet(viewsets.ModelViewSet):
    queryset = OutboundOrder.objects.all().order_by('-created_at')
    serializer_class = OutboundOrderSerializer

    @action(detail=True, methods=['get'], url_path='picking-list')
    def picking_list(self, request, pk=None):
        order = self.get_object()
        lines = order.lines.select_related('product').all()

        result = []
        for line in lines:
            remaining = line.quantity_requested - line.quantity_picked
            if remaining <= 0:
                continue

            stock_qs = (
                StockItem.objects.filter(product=line.product, quantity__gt=0)
                .select_related('bin', 'bin__rack', 'bin__rack__aisle', 'bin__rack__aisle__zone', 'bin__rack__aisle__zone__warehouse')
                .order_by('expiry_date', 'created_at', 'id')
            )

            picks = []
            qty_to_allocate = remaining
            for s in stock_qs:
                if qty_to_allocate <= 0:
                    break
                take = min(s.quantity, qty_to_allocate)
                picks.append(
                    {
                        'bin': s.bin_id,
                        'available': str(s.quantity),
                        'suggested_pick': str(take),
                        'batch_number': s.batch_number,
                        'serial_number': s.serial_number,
                        'expiry_date': s.expiry_date,
                    }
                )
                qty_to_allocate -= take

            result.append(
                {
                    'order_line': line.id,
                    'product': line.product_id,
                    'quantity_remaining': str(remaining),
                    'suggested_picks': picks,
                }
            )

        return Response(result)


class OutboundOrderLineViewSet(viewsets.ModelViewSet):
    queryset = OutboundOrderLine.objects.select_related('order', 'product').all()
    serializer_class = OutboundOrderLineSerializer


class PickConfirmationViewSet(viewsets.ModelViewSet):
    queryset = PickConfirmation.objects.select_related('order_line', 'from_bin', 'to_bin').all().order_by('-created_at')
    serializer_class = PickConfirmationSerializer
