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
