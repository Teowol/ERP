from django.shortcuts import render, get_object_or_404
from django.db.models import Q
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
    }
    return render(request, "production/order_detail.html", context)