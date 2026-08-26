from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from inventory.models import Product, Stock, Warehouse
from production.models import ProductionOrder

from .models import Customer, SalesOrder, SalesOrderLine


def sales_order_list(request):
    """Satış siparişlerini listele ve filtrele."""
    queryset = SalesOrder.objects.select_related("customer").prefetch_related("lines")

    status_filter = request.GET.get("status", "").strip()
    customer_filter = request.GET.get("customer", "").strip()
    query = request.GET.get("q", "").strip()

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    if customer_filter:
        queryset = queryset.filter(customer_id=customer_filter)

    if query:
        queryset = queryset.filter(
            Q(order_number__icontains=query)
            | Q(customer__name__icontains=query)
            | Q(customer__code__icontains=query)
        )

    context = {
        "orders": queryset,
        "customers": Customer.objects.filter(is_active=True),
        "status_choices": SalesOrder.Status.choices,
        "current_status": status_filter,
        "current_customer": customer_filter,
        "current_query": query,
    }
    return render(request, "distribution/sales_order_list.html", context)


def sales_order_detail(request, pk):
    """Sipariş detayını göster."""
    order = get_object_or_404(
        SalesOrder.objects.prefetch_related("lines__product"),
        pk=pk,
    )

    # Her kalem için kullanılabilir mamul stoku
    warehouse = Warehouse.objects.filter(code="DEP-MM").first()
    stock_map = {}
    if warehouse:
        for line in order.lines.all():
            stock = Stock.objects.filter(
                product=line.product,
                warehouse=warehouse,
            ).first()
            stock_map[line.pk] = stock.available_quantity if stock else Decimal("0")

    context = {
        "order": order,
        "warehouse": warehouse,
        "stock_map": stock_map,
        "linked_production_orders": ProductionOrder.objects.filter(
            reference_order_number=order.order_number,
        ),
    }
    return render(request, "distribution/sales_order_detail.html", context)


def sales_order_create(request):
    """Yeni sipariş oluştur."""
    customers = Customer.objects.filter(is_active=True)
    products = Product.objects.filter(
        product_type=Product.ProductType.FINISHED_GOOD,
        is_active=True,
    )

    if request.method == "POST":
        customer_id = request.POST.get("customer")
        order_number = request.POST.get("order_number", "").strip()
        requested_delivery_date = request.POST.get("requested_delivery_date")
        promised_delivery_date = request.POST.get("promised_delivery_date")
        note = request.POST.get("note", "").strip()

        if not customer_id or not order_number:
            messages.error(request, "Müşteri ve sipariş numarası zorunludur.")
        elif SalesOrder.objects.filter(order_number=order_number).exists():
            messages.error(request, "Bu sipariş numarası zaten kullanılıyor.")
        else:
            with transaction.atomic():
                order = SalesOrder.objects.create(
                    customer_id=customer_id,
                    order_number=order_number,
                    requested_delivery_date=requested_delivery_date or None,
                    promised_delivery_date=promised_delivery_date or None,
                    note=note,
                )

                line_count = int(request.POST.get("line_count", "0"))
                for i in range(1, line_count + 1):
                    product_id = request.POST.get(f"product_{i}")
                    quantity = request.POST.get(f"quantity_{i}")
                    unit_price = request.POST.get(f"unit_price_{i}")

                    if product_id and quantity and unit_price:
                        SalesOrderLine.objects.create(
                            sales_order=order,
                            product_id=product_id,
                            quantity=quantity,
                            unit_price=unit_price,
                        )

            messages.success(request, "Sipariş başarıyla oluşturuldu.")
            return redirect("distribution:sales_order_detail", pk=order.pk)

    context = {
        "customers": customers,
        "products": products,
        "today": timezone.now().date().isoformat(),
    }
    return render(request, "distribution/sales_order_create.html", context)


def sales_order_confirm(request, pk):
    """Siparişi onayla ve stok rezervasyonu yap."""
    order = get_object_or_404(SalesOrder, pk=pk)

    if order.status != SalesOrder.Status.DRAFT:
        messages.error(request, "Sadece taslak siparişler onaylanabilir.")
        return redirect("distribution:sales_order_detail", pk=order.pk)

    warehouse = Warehouse.objects.filter(code="DEP-MM").first()
    if not warehouse:
        messages.error(request, "Mamul deposu (DEP-MM) bulunamadı.")
        return redirect("distribution:sales_order_detail", pk=order.pk)

    with transaction.atomic():
        for line in order.lines.select_related("product"):
            stock = Stock.objects.select_for_update().filter(
                product=line.product,
                warehouse=warehouse,
            ).first()

            if not stock:
                messages.error(
                    request,
                    f"{line.product} için mamul deposunda stok kaydı bulunamadı.",
                )
                return redirect("distribution:sales_order_detail", pk=order.pk)

            if stock.available_quantity < line.quantity:
                messages.error(
                    request,
                    f"{line.product} için yeterli stok yok. "
                    f"Kullanılabilir: {stock.available_quantity}, Talep: {line.quantity}",
                )
                return redirect("distribution:sales_order_detail", pk=order.pk)

        for line in order.lines.select_related("product"):
            stock = Stock.objects.get(
                product=line.product,
                warehouse=warehouse,
            )
            stock.reserved_quantity += line.quantity
            stock.save()

        order.status = SalesOrder.Status.CONFIRMED
        order.save()

    messages.success(request, "Sipariş onaylandı ve stok rezerve edildi.")
    return redirect("distribution:sales_order_detail", pk=order.pk)


def sales_order_cancel(request, pk):
    """Siparişi iptal et ve rezervasyonları kaldır."""
    order = get_object_or_404(SalesOrder, pk=pk)

    if order.status in [SalesOrder.Status.SHIPPED, SalesOrder.Status.COMPLETED]:
        messages.error(request, "Sevk edilmiş veya tamamlanmış sipariş iptal edilemez.")
        return redirect("distribution:sales_order_detail", pk=order.pk)

    warehouse = Warehouse.objects.filter(code="DEP-MM").first()

    with transaction.atomic():
        if order.status in [SalesOrder.Status.CONFIRMED, SalesOrder.Status.IN_PRODUCTION, SalesOrder.Status.READY_TO_SHIP]:
            for line in order.lines.select_related("product"):
                if warehouse:
                    stock = Stock.objects.filter(
                        product=line.product,
                        warehouse=warehouse,
                    ).first()
                    if stock:
                        stock.reserved_quantity = max(
                            Decimal("0"),
                            stock.reserved_quantity - line.quantity,
                        )
                        stock.save()

        order.status = SalesOrder.Status.CANCELLED
        order.save()

    messages.success(request, "Sipariş iptal edildi.")
    return redirect("distribution:sales_order_detail", pk=order.pk)
