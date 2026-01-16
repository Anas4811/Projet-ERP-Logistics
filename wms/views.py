from django.db.models import Sum
from django.shortcuts import render

# Create your views here.


def dashboard(request):
    from .models import Bin, Product, StockItem, Warehouse

    counts = {
        'warehouses': Warehouse.objects.count(),
        'bins': Bin.objects.count(),
        'products': Product.objects.count(),
        'stock_items': StockItem.objects.count(),
    }

    stock_rows = (
        StockItem.objects.values('bin__rack__aisle__zone__warehouse__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('bin__rack__aisle__zone__warehouse__name')
    )
    stock_per_warehouse = [
        {
            'name': r['bin__rack__aisle__zone__warehouse__name'],
            'total_qty': r['total_qty'] or 0,
        }
        for r in stock_rows
    ]

    return render(
        request,
        'wms/dashboard.html',
        {
            'counts': counts,
            'stock_per_warehouse': stock_per_warehouse,
        },
    )
