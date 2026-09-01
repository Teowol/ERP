from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from production.models import ProductionOrder
from quality.models import QualityCheck

from .models import Lot, Product, Stock, StockMovement, Warehouse


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


def lot_tracking_list(request):
    """Lot bazlı takip ekranı; üretim ve stok bağlamında hangi parti ne kadar kaldığını gösterir."""
    queryset = Lot.objects.select_related("product", "product__category").all()

    product_filter = request.GET.get("product", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if product_filter:
        queryset = queryset.filter(
            Q(product__code__icontains=product_filter)
            | Q(product__name__icontains=product_filter)
            | Q(lot_number__icontains=product_filter)
        )

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    lots = []
    for lot in queryset:
        remaining = lot.remaining_quantity
        usage_rate = (Decimal("100") * remaining / lot.initial_quantity) if lot.initial_quantity else Decimal("0")
        usage_percent = max(Decimal("0"), min(usage_rate, Decimal("100")))
        lots.append({
            "lot": lot,
            "remaining": remaining,
            "usage_rate": usage_rate,
            "usage_percent": usage_percent,
        })

    context = {
        "lots": lots,
        "statuses": Lot.Status.choices,
        "current_product": product_filter,
        "current_status": status_filter,
    }
    return render(request, "inventory/lot_tracking_list.html", context)


def fire_tracking_list(request):
    """Üretim fire / hurda kayıtlarını takip eder; ürün, emir ve sonuç bazlı filtreleme sunar."""
    queryset = QualityCheck.objects.select_related(
        "production_order",
        "production_order__product",
        "checked_by",
    ).filter(scrapped_quantity__gt=0).order_by("-check_date")

    product_filter = request.GET.get("product", "").strip()
    result_filter = request.GET.get("result", "").strip()

    if product_filter:
        queryset = queryset.filter(
            Q(production_order__order_number__icontains=product_filter)
            | Q(production_order__product__code__icontains=product_filter)
            | Q(production_order__product__name__icontains=product_filter)
        )

    if result_filter:
        queryset = queryset.filter(result=result_filter)

    fire_rows = []
    for check in queryset:
        fire_rate = (
            (Decimal("100") * check.scrapped_quantity / check.checked_quantity)
            if check.checked_quantity
            else Decimal("0")
        )
        fire_rows.append({
            "check": check,
            "fire_rate": max(Decimal("0"), min(fire_rate, Decimal("100"))),
        })

    context = {
        "fire_rows": fire_rows,
        "result_choices": QualityCheck.Result.choices,
        "current_product": product_filter,
        "current_result": result_filter,
    }
    return render(request, "inventory/fire_tracking_list.html", context)


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
