from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.views.decorators.http import require_POST
from .models import ProductionOrder


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
        "available_actions": _get_available_actions(order),
    }
    return render(request, "production/order_detail.html", context)


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