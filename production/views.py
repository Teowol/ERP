from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from inventory.models import Product, Stock, Warehouse
from production.models import (
    BillOfMaterial,
    ProductionCost,
    ProductionLine,
    ProductionOrder,
    ProductionOrderOperation,
    Routing,
)
from quality.models import QualityCheck

from distribution.models import Customer, SalesOrder, SalesOrderLine


def order_list(request):
    """Üretim emirlerini listeleme ve filtreleme görünümü."""
    queryset = ProductionOrder.objects.select_related(
        "product",
        "production_line",
        "bill_of_material",
        "routing",
        "raw_materials_warehouse",
        "finished_goods_warehouse",
    ).all()

    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    priority_filter = request.GET.get("priority", "").strip()

    if query:
        queryset = queryset.filter(
            Q(order_number__icontains=query) |
            Q(product__name__icontains=query) |
            Q(product__code__icontains=query)
        )

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    if priority_filter:
        queryset = queryset.filter(priority=priority_filter)

    context = {
        "orders": queryset,
        "current_query": query,
        "current_status": status_filter,
        "current_priority": priority_filter,
        "status_choices": ProductionOrder.Status.choices,
        "priority_choices": ProductionOrder.Priority.choices,
        "quality_result_choices": QualityCheck.Result.choices,
    }
    return render(request, "production/order_list.html", context)


def order_detail(request, pk):
    """Üretim emri detay, hammadde ve operasyon görünümü."""
    order = get_object_or_404(
        ProductionOrder.objects.select_related(
            "product",
            "production_line",
            "bill_of_material",
            "routing",
            "raw_materials_warehouse",
            "finished_goods_warehouse",
            "created_by",
        ),
        pk=pk,
    )
    components = order.order_components.select_related("component").all()
    operations = order.order_operations.select_related(
        "routing_operation",
        "routing_operation__work_center",
    ).all()

    context = {
        "order": order,
        "components": components,
        "operations": operations,
        "cost_summary": getattr(order, "production_cost", None),
        "available_actions": _get_available_actions(order),
    }
    return render(request, "production/order_detail.html", context)


def cost_list(request):
    """Üretim maliyetlerinin özet listesi."""
    queryset = ProductionCost.objects.select_related(
        "production_order",
        "production_order__product",
        "product",
        "lot",
    ).all()

    order_filter = request.GET.get("order", "").strip()
    if order_filter:
        queryset = queryset.filter(
            Q(production_order__order_number__icontains=order_filter)
            | Q(product__name__icontains=order_filter)
            | Q(product__code__icontains=order_filter)
        )

    context = {
        "costs": queryset.order_by("-calculation_date", "-pk"),
        "current_order": order_filter,
    }
    return render(request, "production/cost_list.html", context)


@require_POST
def production_order_action(request, pk, action):
    """Üretim emri üzerinde durum aksiyonları çalıştırır."""
    order = get_object_or_404(ProductionOrder, pk=pk)

    allowed_actions = _get_available_actions(order)
    if action not in allowed_actions:
        messages.error(request, "Bu işlem mevcut durumda yapılamaz.")
        return redirect("production:order_detail", pk=pk)

    try:
        if action == "release":
            order.release()
            messages.success(request, f"{order.order_number} serbest bırakıldı.")
        elif action == "start":
            order.start_production()
            messages.success(request, f"{order.order_number} üretime başlatıldı.")
        elif action == "quality_check":
            order.send_to_quality_check()
            messages.success(request, f"{order.order_number} kalite kontrole gönderildi.")
        elif action == "complete":
            order.complete_production(user=request.user)
            messages.success(request, f"{order.order_number} tamamlandı ve mamul stoğa girdi.")
        elif action == "cancel":
            order.cancel()
            messages.success(request, f"{order.order_number} iptal edildi.")
        else:
            messages.error(request, "Bilinmeyen aksiyon.")
    except Exception as exc:
        messages.error(request, f"İşlem başarısız: {exc}")

    return redirect("production:order_detail", pk=pk)


def _get_available_actions(order):
    """Mevcut duruma göre izin verilen aksiyonları döner."""
    if order.status == ProductionOrder.Status.PLANNED:
        return ["release", "cancel"]
    if order.status == ProductionOrder.Status.RELEASED:
        return ["start", "cancel"]
    if order.status == ProductionOrder.Status.IN_PROGRESS:
        return ["quality_check", "complete", "cancel"]
    if order.status == ProductionOrder.Status.QUALITY_CHECK:
        return ["complete", "cancel"]
    return []

def operation_list(request):
    """Tüm üretim emri operasyonlarını listeleme ve filtreleme."""
    operations = ProductionOrderOperation.objects.select_related(
        "production_order",
        "production_order__product",
        "routing_operation",
        "routing_operation__work_center",
    ).all()

    order_filter = request.GET.get("order", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if order_filter:
        operations = operations.filter(
            Q(production_order__order_number__icontains=order_filter)
            | Q(production_order__product__name__icontains=order_filter)
        )

    if status_filter:
        operations = operations.filter(status=status_filter)

    context = {
        "operations": operations,
        "current_order": order_filter,
        "current_status": status_filter,
        "status_choices": ProductionOrderOperation.Status.choices,
    }
    return render(request, "production/operation_list.html", context)


@require_POST
def operation_action(request, pk, action):
    """Üretim emri operasyonu üzerinde aksiyon çalıştırır."""
    operation = get_object_or_404(
        ProductionOrderOperation.objects.select_related(
            "production_order",
            "routing_operation",
        ),
        pk=pk,
    )
    order = operation.production_order

    try:
        if action == "start":
            operation.start(user=request.user)
            messages.success(
                request,
                f"{operation.routing_operation.name} başlatıldı.",
            )

        elif action == "pause":
            operation.pause(user=request.user)
            messages.success(
                request,
                f"{operation.routing_operation.name} duraklatıldı.",
            )

        elif action == "resume":
            operation.start(user=request.user)
            messages.success(
                request,
                f"{operation.routing_operation.name} devam ettirildi.",
            )

        elif action == "complete":
            quantity_text = request.POST.get("completed_quantity", "").strip()

            if quantity_text:
                completed_quantity = Decimal(quantity_text)
            else:
                completed_quantity = order.planned_quantity

            if completed_quantity > order.planned_quantity:
                raise ValueError(
                    "Tamamlanan miktar planlanan miktardan fazla olamaz."
                )

            operation.complete(
                completed_quantity=completed_quantity,
                user=request.user,
            )
            messages.success(
                request,
                f"{operation.routing_operation.name} tamamlandı.",
            )

        else:
            messages.error(request, "Bilinmeyen operasyon aksiyonu.")

    except Exception as exc:
        messages.error(request, f"İşlem başarısız: {exc}")

    return redirect("production:order_detail", pk=order.pk)