from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Invoice, SalesOrder


@shared_task
def notify_sales_order_confirmed(order_pk):
    """Sipariş onaylandığında fatura oluştur ve bildirim e-postası gönder."""
    try:
        order = SalesOrder.objects.select_related("customer").get(pk=order_pk)
    except SalesOrder.DoesNotExist:
        return f"Sipariş bulunamadı: {order_pk}"

    tax_rate = Decimal("20.00")
    tax_factor = tax_rate / Decimal("100")
    total_with_tax = order.total_amount * (Decimal("1") + tax_factor)

    # Fatura oluştur (henüz yoksa)
    invoice, created = Invoice.objects.get_or_create(
        sales_order=order,
        defaults={
            "customer": order.customer,
            "issue_date": timezone.now().date(),
            "due_date": timezone.now().date() + timedelta(days=30),
            "subtotal": order.total_amount,
            "tax_rate": tax_rate,
            "tax_amount": order.total_amount * tax_factor,
            "total_amount": total_with_tax,
            "status": Invoice.Status.ISSUED,
        },
    )

    recipient = getattr(settings, "ERP_NOTIFICATION_EMAIL", None)

    if not recipient:
        return "ERP_NOTIFICATION_EMAIL tanımlı değil."

    subject = f"Sipariş Onaylandı - {order.order_number}"
    message = (
        f"Sayın {order.customer.name},\n\n"
        f"{order.order_number} numaralı siparişiniz onaylanmıştır.\n"
        f"Fatura numarası: {invoice.invoice_number}\n"
        f"Sipariş toplamı: {order.total_amount}\n"
        f"KDV dahil toplam: {invoice.total_amount}\n"
        f"Taahhüt edilen teslim tarihi: {order.promised_delivery_date or 'Belirtilmedi'}\n\n"
        f"Sipariş detaylarınız için ERP sistemine giriş yapabilirsiniz.\n"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@erp.local"),
        recipient_list=[recipient],
        fail_silently=False,
    )

    status = "oluşturuldu" if created else "zaten mevcuttu"
    return f"Fatura {status}: {invoice.invoice_number} | E-posta gönderildi: {recipient}"

@shared_task
def process_order_fulfillment_task(order_pk, user_id=None):
    """
    Müşteri siparişini asenkron olarak işler:
    - Depoda stok varsa rezerve edip kargo (Shipment) kaydı oluşturur.
    - Stok yetersizse eksik kısım için Üretim Emri (ProductionOrder) açar.
    """
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from inventory.models import Stock, StockMovement, Warehouse
    from logistics.models import Shipment
    from production.models import BillOfMaterial, ProductionLine, ProductionOrder, Routing
    import uuid

    User = get_user_model()
    user = User.objects.filter(pk=user_id).first() if user_id else None

    try:
        order = SalesOrder.objects.prefetch_related("lines__product").get(pk=order_pk)
    except SalesOrder.DoesNotExist:
        return f"Sipariş bulunamadı: {order_pk}"

    fg_wh = Warehouse.objects.filter(code="DEP-MM").first()
    raw_wh = Warehouse.objects.filter(code="DEP-HM").first()
    if not fg_wh:
        return "Mamul deposu (DEP-MM) bulunamadı."

    all_shipped = True

    with transaction.atomic():
        for line in order.lines.select_related("product"):
            stock, _ = Stock.objects.select_for_update().get_or_create(
                product=line.product,
                warehouse=fg_wh,
                defaults={"quantity": Decimal("0"), "reserved_quantity": Decimal("0")},
            )
            available = stock.available_quantity

            # Bu kalem için zaten sevkiyat/üretim işlemi yapılmışsa tekrar işlem yapma
            already_shipped = Shipment.objects.filter(sales_order_line=line).exists()
            already_in_production = ProductionOrder.objects.filter(
                reference_order_number=order.order_number, product=line.product
            ).exists()
            if already_shipped or already_in_production:
                if already_in_production:
                    all_shipped = False
                continue

            # 1. Senaryo: Depoda yeterli ürün var -> Doğrudan Kargoya Ver
            if available >= line.quantity:
                # Stoktan düşüş ve hareket kaydı
                stock.quantity -= line.quantity
                stock.save(update_fields=["quantity", "updated_at"])

                StockMovement.objects.create(
                    product=line.product,
                    warehouse=fg_wh,
                    movement_type=StockMovement.MovementType.OUT,
                    quantity=line.quantity,
                    reference_type="SalesOrder",
                    reference_id=order.pk,
                    note=f"Sipariş {order.order_number} sevkiyat çıkışı",
                )

                # Kargo / Sevkiyat kaydı oluştur
                shipment_no = f"SHP-{order.order_number}-{uuid.uuid4().hex[:4].upper()}"
                Shipment.objects.create(
                    shipment_number=shipment_no,
                    sales_order=order,
                    sales_order_line=line,
                    warehouse=fg_wh,
                    quantity=line.quantity,
                    status=Shipment.Status.SHIPPED,
                    shipped_at=timezone.now(),
                    note="Otomatik depo çıkışı ve kargolama",
                )

                line.shipped_quantity = line.quantity
                line.save(update_fields=["shipped_quantity"])
                continue

            # 2. Senaryo: Stok yetersiz -> Eksik kısım için Üretim Emri
            all_shipped = False
            shortfall = line.quantity - max(available, Decimal("0"))

            if available > 0:
                stock.reserved_quantity += available
                stock.save(update_fields=["reserved_quantity", "updated_at"])

            bom = BillOfMaterial.objects.filter(
                product=line.product, status=BillOfMaterial.Status.ACTIVE
            ).first()
            routing = Routing.objects.filter(
                product=line.product, status=Routing.Status.ACTIVE
            ).first()
            prod_line = ProductionLine.objects.filter(is_active=True).first()

            if not bom or not routing or not raw_wh or not prod_line:
                continue

            timestamp = timezone.now().strftime("%y%m%d%H%M%S")
            po_number = f"PO-{order.order_number}-{line.pk}-{timestamp[-4:]}"

            # Varsa mevcut üretim emrini tekrar oluşturmayalım
            po, po_created = ProductionOrder.objects.get_or_create(
                reference_order_number=order.order_number,
                product=line.product,
                defaults={
                    "order_number": po_number,
                    "bill_of_material": bom,
                    "routing": routing,
                    "production_line": prod_line,
                    "raw_materials_warehouse": raw_wh,
                    "finished_goods_warehouse": fg_wh,
                    "planned_quantity": shortfall,
                    "created_by": user or order.customer.user or User.objects.filter(is_superuser=True).first(),
                    "planned_start_date": timezone.now(),
                    "planned_end_date": order.promised_delivery_date or timezone.now(),
                    "status": ProductionOrder.Status.PLANNED,
                },
            )
            if po_created:
                po.create_components_from_bom()
                po.create_operations_from_routing()
                try:
                    po.release()
                    po.start_production()
                except ValueError:
                    pass

        if all_shipped:
            order.status = SalesOrder.Status.SHIPPED
        else:
            order.status = SalesOrder.Status.IN_PRODUCTION
        order.save(update_fields=["status", "updated_at"])

    return f"Sipariş {order.order_number} işlendi. Durum: {order.status}"