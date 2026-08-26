from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.db import models

from .models import Stock, Warehouse


@shared_task
def check_critical_stock_levels():
    """Kritik stok seviyesinin altına düşen ürünleri tespit edip raporla."""
    low_stock = Stock.objects.select_related("product", "warehouse").filter(
        quantity__lte=models.F("minimum_stock_level")
    )

    lines = []
    for item in low_stock:
        lines.append(
            f"- {item.product.name} ({item.product.code}) | "
            f"Depo: {item.warehouse.name} | "
            f"Mevcut: {item.quantity} | Min: {item.minimum_stock_level}"
        )

    if not lines:
        return "Kritik stok seviyesinin altında ürün bulunmamaktadır."

    message = "Kritik Stok Uyarısı\n\n" + "\n".join(lines)

    send_mail(
        subject="ERP: Kritik Stok Uyarısı",
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@erp.local"),
        recipient_list=["admin@example.com"],
        fail_silently=True,
    )

    return f"{len(lines)} ürün için kritik stok uyarısı gönderildi."

