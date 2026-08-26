from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Product, Stock, StockMovement, Warehouse


def stock_level_list(request):
    """Depo bazlı stok seviyelerini listele ve filtrele."""
    queryset = Stock.objects.select_related(
        "product",
        "product__category",
        "warehouse",
    ).all()

    product_filter = request.GET.get("product", "").strip()
    warehouse_filter = request.GET.get("warehouse", "").strip()
    low_stock_filter = request.GET.get("low_stock", "").strip()

    if product_filter:
        queryset = queryset.filter(
            Q(product__code__icontains=product_filter)
            | Q(product__name__icontains=product_filter)
        )

    if warehouse_filter:
        queryset = queryset.filter(warehouse_id=warehouse_filter)

    if low_stock_filter == "1":
        queryset = queryset.filter(quantity__lte=models.F("product__minimum_stock_level"))

    context = {
        "stocks": queryset,
        "warehouses": Warehouse.objects.filter(is_active=True),
        "current_product": product_filter,
        "current_warehouse": warehouse_filter,
        "current_low_stock": low_stock_filter,
    }
    return render(request, "inventory/stock_level_list.html", context)


def stock_movement_list(request):
    """Stok hareketlerini listele ve filtrele."""
    queryset = StockMovement.objects.select_related(
        "product",
        "warehouse",
    ).all()

    product_filter = request.GET.get("product", "").strip()
    warehouse_filter = request.GET.get("warehouse", "").strip()
    movement_type_filter = request.GET.get("movement_type", "").strip()

    if product_filter:
        queryset = queryset.filter(
            Q(product__code__icontains=product_filter)
            | Q(product__name__icontains=product_filter)
        )

    if warehouse_filter:
        queryset = queryset.filter(warehouse_id=warehouse_filter)

    if movement_type_filter:
        queryset = queryset.filter(movement_type=movement_type_filter)

    context = {
        "movements": queryset,
        "warehouses": Warehouse.objects.filter(is_active=True),
        "movement_types": StockMovement.MovementType.choices,
        "current_product": product_filter,
        "current_warehouse": warehouse_filter,
        "current_movement_type": movement_type_filter,
    }
    return render(request, "inventory/stock_movement_list.html", context)


def product_movement_history(request, product_pk):
    """Belirli bir ürünün tüm stok hareketleri."""
    product = get_object_or_404(Product, pk=product_pk)

    movements = StockMovement.objects.select_related("warehouse").filter(
        product=product
    )

    context = {
        "product": product,
        "movements": movements,
    }
    return render(request, "inventory/product_movement_history.html", context)
