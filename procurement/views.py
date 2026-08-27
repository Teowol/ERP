from django.shortcuts import render

from .models import PurchaseOrder, PurchaseRequest, Supplier


def purchase_request_list(request):
    context = {
        "suppliers_count": Supplier.objects.filter(is_active=True).count(),
        "pending_requests_count": PurchaseRequest.objects.filter(
            status=PurchaseRequest.Status.PENDING_APPROVAL
        ).count(),
        "approved_requests_count": PurchaseRequest.objects.filter(
            status=PurchaseRequest.Status.APPROVED
        ).count(),
        "orders_count": PurchaseOrder.objects.exclude(
            status=PurchaseOrder.Status.CANCELLED
        ).count(),
        "recent_requests": PurchaseRequest.objects.select_related(
            "requested_by"
        ).prefetch_related("lines")[:10],
    }

    return render(request, "procurement/procurement.html", context)