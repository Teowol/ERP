from django.db import models


class Shipment(models.Model):
    """Sipariş kalemine bağlı kargo/sevkiyat kaydı."""

    class Status(models.TextChoices):
        PENDING = "pending", "Hazırlanıyor"
        SHIPPED = "shipped", "Kargoya Verildi"
        DELIVERED = "delivered", "Teslim Edildi"
        CANCELLED = "cancelled", "İptal Edildi"

    shipment_number = models.CharField(max_length=50, unique=True, verbose_name="Sevkiyat No")
    sales_order = models.ForeignKey(
        "distribution.SalesOrder",
        on_delete=models.PROTECT,
        related_name="shipments",
        verbose_name="Satış Siparişi",
    )
    sales_order_line = models.ForeignKey(
        "distribution.SalesOrderLine",
        on_delete=models.PROTECT,
        related_name="shipments",
        null=True,
        blank=True,
        verbose_name="Sipariş Kalemi",
    )
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="shipments",
        verbose_name="Depo",
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3, verbose_name="Miktar")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Durum",
    )
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name="Kargoya Veriliş Tarihi")
    note = models.TextField(blank=True, verbose_name="Not")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Sevkiyat"
        verbose_name_plural = "Sevkiyatlar"

    def __str__(self):
        return f"{self.shipment_number} - {self.sales_order}"
