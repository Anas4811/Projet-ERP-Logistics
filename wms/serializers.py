from decimal import Decimal
from datetime import date
from typing import Optional

from django.db import transaction
from django.db.models import Q, Sum
from rest_framework import serializers

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


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'location', 'capacity']


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ['id', 'warehouse', 'name']


class AisleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aisle
        fields = ['id', 'zone', 'name']


class RackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rack
        fields = ['id', 'aisle', 'name']


class BinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bin
        fields = ['id', 'rack', 'name', 'capacity']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'category',
            'sku',
            'unit',
            'default_batch_number',
            'default_expiry_date',
        ]


class StockItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockItem
        fields = [
            'id',
            'bin',
            'product',
            'quantity',
            'batch_number',
            'serial_number',
            'expiry_date',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class PutawayRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PutawayRule
        fields = ['id', 'priority', 'product', 'product_category', 'zone']


def _bin_used_qty(bin_obj: Bin) -> Decimal:
    result = bin_obj.stock_items.aggregate(total=Sum('quantity'))
    return result['total'] or Decimal('0')


def _ensure_bin_capacity(bin_obj: Bin, additional_qty: Decimal) -> None:
    if additional_qty <= 0:
        return
    if bin_obj.capacity is None or bin_obj.capacity == 0:
        return
    used = _bin_used_qty(bin_obj)
    if used + additional_qty > bin_obj.capacity:
        raise serializers.ValidationError({'to_bin': 'Bin capacity exceeded.'})


def suggest_putaway_bin(*, product: Product, qty: Decimal, warehouse: Optional[Warehouse]) -> Bin:
    rule_qs = PutawayRule.objects.select_related('zone', 'zone__warehouse').filter(
        Q(product=product)
        | Q(product_category=product.category)
        | (Q(product__isnull=True) & Q(product_category__isnull=True))
    )
    if warehouse is not None:
        rule_qs = rule_qs.filter(zone__warehouse=warehouse)

    rules = list(rule_qs.order_by('priority', 'id'))
    if not rules:
        fallback = PutawayRule.objects.select_related('zone', 'zone__warehouse').all()
        if warehouse is not None:
            fallback = fallback.filter(zone__warehouse=warehouse)
        rules = list(fallback.order_by('priority', 'id')[:50])

    zone_ids = sorted({r.zone_id for r in rules})
    if not zone_ids:
        raise serializers.ValidationError({'to_bin': 'No putaway zones available.'})

    bins_qs = (
        Bin.objects.filter(rack__aisle__zone_id__in=zone_ids)
        .select_related('rack', 'rack__aisle', 'rack__aisle__zone')
        .annotate(used_qty=Sum('stock_items__quantity'))
    )

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
        raise serializers.ValidationError({'to_bin': 'No bin has enough free capacity.'})

    return best


@transaction.atomic
def apply_stock_delta(
    *,
    bin_obj: Bin,
    product: Product,
    delta_qty: Decimal,
    batch_number: Optional[str],
    serial_number: Optional[str],
    expiry_date: Optional[date],
) -> StockItem:
    if delta_qty == 0:
        raise serializers.ValidationError('Quantity delta cannot be 0.')

    key = {
        'bin': bin_obj,
        'product': product,
        'batch_number': batch_number,
        'serial_number': serial_number,
        'expiry_date': expiry_date,
    }

    stock_qs = StockItem.objects.select_for_update().filter(**key)
    stock = stock_qs.first()

    if delta_qty > 0:
        _ensure_bin_capacity(bin_obj, delta_qty)
        if stock is None:
            stock = StockItem.objects.create(**key, quantity=delta_qty)
        else:
            stock.quantity = stock.quantity + delta_qty
            stock.save(update_fields=['quantity', 'updated_at'])
        return stock

    delta_qty_abs = -delta_qty
    if stock is None:
        raise serializers.ValidationError('Insufficient stock for movement.')

    if stock.quantity < delta_qty_abs:
        raise serializers.ValidationError('Insufficient stock for movement.')

    stock.quantity = stock.quantity - delta_qty_abs
    stock.save(update_fields=['quantity', 'updated_at'])
    return stock


class StockMovementSerializer(serializers.ModelSerializer):
    warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = StockMovement
        fields = [
            'id',
            'movement_type',
            'reference',
            'warehouse',
            'product',
            'quantity',
            'from_bin',
            'to_bin',
            'batch_number',
            'serial_number',
            'expiry_date',
            'created_at',
        ]
        read_only_fields = ['created_at']

    def validate(self, attrs):
        movement_type = attrs.get('movement_type')
        from_bin = attrs.get('from_bin')
        to_bin = attrs.get('to_bin')

        if movement_type in {StockMovement.MovementType.RECEIPT}:
            if to_bin is None and attrs.get('warehouse') is None:
                raise serializers.ValidationError({'warehouse': 'Provide warehouse when using auto putaway (to_bin omitted).'} )

        if movement_type in {
            StockMovement.MovementType.ISSUE,
            StockMovement.MovementType.PICK,
        }:
            if from_bin is None:
                raise serializers.ValidationError({'from_bin': 'Required for issue/adjustment/pick.'})

        if movement_type in {StockMovement.MovementType.ADJUSTMENT}:
            if from_bin is None and to_bin is None:
                raise serializers.ValidationError('Either from_bin (decrease) or to_bin (increase) is required for adjustment.')
            if from_bin is not None and to_bin is not None:
                raise serializers.ValidationError('For adjustment, provide only one of from_bin or to_bin.')

        if movement_type in {
            StockMovement.MovementType.TRANSFER,
            StockMovement.MovementType.PUTAWAY,
        }:
            if from_bin is None or to_bin is None:
                raise serializers.ValidationError('Both from_bin and to_bin are required for transfer/putaway.')

        if from_bin is not None and to_bin is not None:
            if from_bin.id == to_bin.id:
                raise serializers.ValidationError('from_bin and to_bin cannot be the same.')

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        warehouse = validated_data.pop('warehouse', None)

        if validated_data.get('movement_type') == StockMovement.MovementType.RECEIPT and validated_data.get('to_bin') is None:
            suggested = suggest_putaway_bin(product=validated_data['product'], qty=validated_data['quantity'], warehouse=warehouse)
            validated_data['to_bin'] = suggested

        movement = StockMovement.objects.create(**validated_data)

        movement_type = movement.movement_type
        qty = movement.quantity

        if movement_type == StockMovement.MovementType.RECEIPT:
            apply_stock_delta(
                bin_obj=movement.to_bin,
                product=movement.product,
                delta_qty=qty,
                batch_number=movement.batch_number,
                serial_number=movement.serial_number,
                expiry_date=movement.expiry_date,
            )

        elif movement_type == StockMovement.MovementType.ADJUSTMENT:
            if movement.from_bin_id is not None:
                apply_stock_delta(
                    bin_obj=movement.from_bin,
                    product=movement.product,
                    delta_qty=-qty,
                    batch_number=movement.batch_number,
                    serial_number=movement.serial_number,
                    expiry_date=movement.expiry_date,
                )
            else:
                apply_stock_delta(
                    bin_obj=movement.to_bin,
                    product=movement.product,
                    delta_qty=qty,
                    batch_number=movement.batch_number,
                    serial_number=movement.serial_number,
                    expiry_date=movement.expiry_date,
                )

        elif movement_type in {StockMovement.MovementType.ISSUE, StockMovement.MovementType.PICK}:
            apply_stock_delta(
                bin_obj=movement.from_bin,
                product=movement.product,
                delta_qty=-qty,
                batch_number=movement.batch_number,
                serial_number=movement.serial_number,
                expiry_date=movement.expiry_date,
            )

        elif movement_type in {StockMovement.MovementType.TRANSFER, StockMovement.MovementType.PUTAWAY}:
            apply_stock_delta(
                bin_obj=movement.from_bin,
                product=movement.product,
                delta_qty=-qty,
                batch_number=movement.batch_number,
                serial_number=movement.serial_number,
                expiry_date=movement.expiry_date,
            )
            apply_stock_delta(
                bin_obj=movement.to_bin,
                product=movement.product,
                delta_qty=qty,
                batch_number=movement.batch_number,
                serial_number=movement.serial_number,
                expiry_date=movement.expiry_date,
            )

        return movement


class OutboundOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutboundOrderLine
        fields = ['id', 'order', 'product', 'quantity_requested', 'quantity_picked']
        read_only_fields = ['quantity_picked']


class OutboundOrderSerializer(serializers.ModelSerializer):
    lines = OutboundOrderLineSerializer(many=True, read_only=True)

    class Meta:
        model = OutboundOrder
        fields = ['id', 'order_number', 'status', 'created_at', 'lines']
        read_only_fields = ['created_at']


class PickConfirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickConfirmation
        fields = [
            'id',
            'order_line',
            'from_bin',
            'to_bin',
            'quantity',
            'batch_number',
            'serial_number',
            'expiry_date',
            'created_at',
        ]
        read_only_fields = ['created_at']

    @transaction.atomic
    def create(self, validated_data):
        pick = PickConfirmation.objects.create(**validated_data)
        line = pick.order_line

        StockMovement.objects.create(
            movement_type=StockMovement.MovementType.PICK,
            reference=line.order.order_number,
            product=line.product,
            quantity=pick.quantity,
            from_bin=pick.from_bin,
            to_bin=pick.to_bin,
            batch_number=pick.batch_number,
            serial_number=pick.serial_number,
            expiry_date=pick.expiry_date,
        )

        apply_stock_delta(
            bin_obj=pick.from_bin,
            product=line.product,
            delta_qty=-pick.quantity,
            batch_number=pick.batch_number,
            serial_number=pick.serial_number,
            expiry_date=pick.expiry_date,
        )

        line.quantity_picked = line.quantity_picked + pick.quantity
        line.save(update_fields=['quantity_picked'])

        if line.quantity_picked >= line.quantity_requested:
            lines = line.order.lines.all()
            if all(l.quantity_picked >= l.quantity_requested for l in lines):
                line.order.status = OutboundOrder.Status.PICKED
                line.order.save(update_fields=['status'])

        return pick
