from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from production.models import ProductionOrder

from .models import QualityCheck


def quality_check_list(request):
    """Kalite kontrol kayıtlarını listele ve filtrele."""
    queryset = QualityCheck.objects.select_related(
        "production_order",
        "production_order__product",
        "checked_by",
    ).all()

    order_filter = request.GET.get("order", "").strip()
    result_filter = request.GET.get("result", "").strip()

    if order_filter:
        queryset = queryset.filter(
            Q(production_order__order_number__icontains=order_filter)
            | Q(production_order__product__name__icontains=order_filter)
        )

    if result_filter:
        queryset = queryset.filter(result=result_filter)

    context = {
        "checks": queryset,
        "current_order": order_filter,
        "current_result": result_filter,
        "result_choices": QualityCheck.Result.choices,
    }
    return render(request, "quality/quality_check_list.html", context)


@login_required
@require_POST
def quality_check_create(request, order_pk):
    """Üretim emrine yeni kalite kontrol kaydı ekle."""
    order = get_object_or_404(
        ProductionOrder,
        pk=order_pk,
        status__in=[ProductionOrder.Status.IN_PROGRESS, ProductionOrder.Status.QUALITY_CHECK],
    )

    try:
        checked_quantity = Decimal(request.POST.get("checked_quantity", "0").strip() or "0")
        accepted_quantity = Decimal(request.POST.get("accepted_quantity", "0").strip() or "0")
        rejected_quantity = Decimal(request.POST.get("rejected_quantity", "0").strip() or "0")
        scrapped_quantity = Decimal(request.POST.get("scrapped_quantity", "0").strip() or "0")
        result = request.POST.get("result", "pass")
        rejection_reason = request.POST.get("rejection_reason", "").strip()
        notes = request.POST.get("notes", "").strip()

        if result not in QualityCheck.Result.values:
            raise ValueError("Geçersiz sonuç değeri.")

        check = QualityCheck(
            production_order=order,
            checked_by=request.user,
            checked_quantity=checked_quantity,
            accepted_quantity=accepted_quantity,
            rejected_quantity=rejected_quantity,
            scrapped_quantity=scrapped_quantity,
            result=result,
            rejection_reason=rejection_reason,
            notes=notes,
        )
        check.full_clean()
        check.save()

        order.scrapped_quantity = (
            order.quality_checks.aggregate(total=models.Sum("scrapped_quantity"))["total__sum"] or Decimal("0")
        )
        order.save(update_fields=["scrapped_quantity"])

        messages.success(request, "Kalite kontrol kaydı eklendi.")

    except (ValidationError, ValueError) as exc:
        messages.error(request, f"Kayıt eklenemedi: {exc}")
    except Exception as exc:
        messages.error(request, f"Beklenmeyen hata: {exc}")

    return redirect("production:order_detail", pk=order_pk)


@login_required
@require_POST
def quality_check_delete(request, pk):
    """Kalite kontrol kaydını sil."""
    check = get_object_or_404(QualityCheck, pk=pk)
    order_pk = check.production_order.pk
    check.delete()

    order = ProductionOrder.objects.get(pk=order_pk)
    order.scrapped_quantity = (
        order.quality_checks.aggregate(total=models.Sum("scrapped_quantity"))["total__sum"] or Decimal("0")
    )
    order.save(update_fields=["scrapped_quantity"])

    messages.success(request, "Kalite kontrol kaydı silindi.")
    return redirect("production:order_detail", pk=order_pk)
