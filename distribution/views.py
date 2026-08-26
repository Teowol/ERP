from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from inventory.models import Product, Stock, Warehouse
from production.models import BillOfMaterial, ProductionLine, ProductionOrder, Routing

from .models import Customer, SalesOrder, SalesOrderLine
from .tasks import notify_sales_order_confirmed


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


def sales_order_edit(request, pk):
    """Taslak durumundaki siparişi ve kalemlerini düzenleme."""
    order = get_object_or_404(SalesOrder.objects.prefetch_related("lines"), pk=pk)

    if order.status != SalesOrder.Status.DRAFT:
        messages.error(request, "Sadece taslak durumundaki siparişler düzenlenebilir.")
        return redirect("distribution:sales_order_detail", pk=order.pk)

    customers = Customer.objects.filter(is_active=True)
    products = Product.objects.filter(
        product_type=Product.ProductType.FINISHED_GOOD,
        is_active=True,
    )

    if request.method == "POST":
        customer_id = request.POST.get("customer")
        requested_delivery_date = request.POST.get("requested_delivery_date")
        promised_delivery_date = request.POST.get("promised_delivery_date")
        note = request.POST.get("note", "").strip()

        if not customer_id:
            messages.error(request, "Müşteri seçimi zorunludur.")
        else:
            with transaction.atomic():
                order.customer_id = customer_id
                order.requested_delivery_date = requested_delivery_date or None
                order.promised_delivery_date = promised_delivery_date or None
                order.note = note
                order.save()

                # Mevcut kalemleri temizleyip yenilerini ekleyelim
                order.lines.all().delete()
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

            messages.success(request, "Sipariş başarıyla güncellendi.")
            return redirect("distribution:sales_order_detail", pk=order.pk)

    context = {
        "order": order,
        "customers": customers,
        "products": products,
    }
    return render(request, "distribution/sales_order_edit.html", context)


def create_production_order_from_line(request, line_pk):
    """Sipariş kaleminden doğrudan üretim emri oluşturma."""
    line = get_object_or_404(
        SalesOrderLine.objects.select_related("sales_order", "product"),
        pk=line_pk,
    )
    order = line.sales_order

    if order.status not in [SalesOrder.Status.CONFIRMED, SalesOrder.Status.IN_PRODUCTION]:
        messages.error(request, "Yalnızca onaylanmış veya üretimdeki siparişler için üretim emri oluşturulabilir.")
        return redirect("distribution:sales_order_detail", pk=order.pk)

    # Ürüne ait aktif BOM ve Routing bulalım
    bom = BillOfMaterial.objects.filter(product=line.product, is_active=True).first()
    if not bom:
        messages.error(request, f"{line.product.name} için aktif bir Reçete (BOM) bulunamadı. Önce BOM tanımlamalısınız.")
        return redirect("distribution:sales_order_detail", pk=order.pk)

    routing = Routing.objects.filter(product=line.product, is_active=True).first()
    if not routing:
        messages.error(request, f"{line.product.name} için aktif bir Rota (Routing) bulunamadı. Önce Rota tanımlamalısınız.")
        return redirect("distribution:sales_order_detail", pk=order.pk)

    raw_wh = Warehouse.objects.filter(code="DEP-HM").first()
    fg_wh = Warehouse.objects.filter(code="DEP-MM").first()
    prod_line = ProductionLine.objects.filter(is_active=True).first()

    if not raw_wh or not fg_wh:
        messages.error(request, "Hammadde (DEP-HM) veya Mamul (DEP-MM) deposu eksik.")
        return redirect("distribution:sales_order_detail", pk=order.pk)

    # Otomatik benzersiz bir emir numarası üretelim
    timestamp = timezone.now().strftime("%y%m%d%H%M%S")
    po_number = f"PO-{order.order_number}-{line.pk}-{timestamp[-4:]}"

    with transaction.atomic():
        po = ProductionOrder.objects.create(
            order_number=po_number,
            product=line.product,
            bill_of_material=bom,
            routing=routing,
            production_line=prod_line,
            raw_materials_warehouse=raw_wh,
            finished_goods_warehouse=fg_wh,
            planned_quantity=line.quantity,
            reference_order_number=order.order_number,
            planned_start_date=timezone.now(),
            planned_end_date=order.promised_delivery_date or timezone.now(),
        )
        # BOM ve Routing operasyonlarını/komponentlerini oluştur
        po.create_components_from_bom()
        po.create_operations_from_routing()

        # Sipariş durumunu 'Üretimde' yap
        if order.status != SalesOrder.Status.IN_PRODUCTION:
            order.status = SalesOrder.Status.IN_PRODUCTION
            order.save()

    messages.success(request, f"{po.order_number} numaralı üretim emri ve operasyon adımları oluşturuldu.")
    return redirect("production:order_detail", pk=po.pk)

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import Invoice


def invoice_pdf(request, invoice_pk):
    """Fatura PDF dosyası oluştur ve indir."""
    invoice = get_object_or_404(
        Invoice.objects.select_related("sales_order", "customer"),
        pk=invoice_pk,
    )
    order = invoice.sales_order

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements = []

    # Başlık
    elements.append(Paragraph("FATURA", styles["Title"]))
    elements.append(Spacer(1, 0.5 * cm))

    # Fatura bilgileri
    info_data = [
        ["Fatura No:", invoice.invoice_number],
        ["Fatura Tarihi:", str(invoice.issue_date)],
        ["Vade Tarihi:", str(invoice.due_date or "-")],
        ["Sipariş No:", order.order_number],
        ["Müşteri:", str(invoice.customer)],
        ["Durum:", invoice.get_status_display()],
    ]
    info_table = Table(info_data, colWidths=[5 * cm, 10 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 1 * cm))

    # Sipariş satırları
    lines = order.lines.select_related("product").all()
    line_data = [["Ürün", "Miktar", "Birim Fiyat", "Toplam"]]
    for line in lines:
        line_data.append([
            str(line.product),
            str(line.quantity),
            f"{line.unit_price:.2f}",
            f"{line.line_total:.2f}",
        ])
    line_data.append(["", "", "KDV (%20):", f"{invoice.tax_amount:.2f}"])
    line_data.append(["", "", "GENEL TOPLAM:", f"{invoice.total_amount:.2f}"])

    line_table = Table(line_data, colWidths=[7 * cm, 3 * cm, 4 * cm, 4 * cm])
    line_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
        ("BACKGROUND", (0, -2), (-1, -1), colors.HexColor("#ecf0f1")),
        ("FONTNAME", (0, -2), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    elements.append(line_table)

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{invoice.invoice_number}.pdf"'
    return response
