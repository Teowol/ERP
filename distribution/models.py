from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Customer(models.Model):
    """Sipariş veren müşteriler."""

    class Meta:
        ordering = ["name"]
        verbose_name = "Müşteri"
        verbose_name_plural = "Müşteriler"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    tax_number = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class SalesOrder(models.Model):
    """Müşteri siparişleri."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Taslak"
        CONFIRMED = "confirmed", "Onaylandı"
        IN_PRODUCTION = "in_production", "Üretimde"
        READY_TO_SHIP = "ready_to_ship", "Sevkiyata Hazır"
        SHIPPED = "shipped", "Sevk Edildi"
        COMPLETED = "completed", "Tamamlandı"
        CANCELLED = "cancelled", "İptal Edildi"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Satış Siparişi"
        verbose_name_plural = "Satış Siparişleri"

    order_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="sales_orders",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    requested_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Talep Edilen Teslim Tarihi",
    )
    promised_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Taahhüt Edilen Teslim Tarihi",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_amount(self):
        return sum(
            line.line_total for line in self.lines.all()
        ) if self.lines.exists() else Decimal("0")

    def __str__(self):
        return f"{self.order_number} - {self.customer}"


class SalesOrderLine(models.Model):
    """Sipariş kalemleri."""

    class Meta:
        ordering = ["id"]
        verbose_name = "Sipariş Kalemi"
        verbose_name_plural = "Sipariş Kalemleri"

    sales_order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.PROTECT,
        related_name="sales_order_lines",
        limit_choices_to={"product_type": "finished_good"},
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    line_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
    )
    produced_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
    )
    shipped_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
    )

    def save(self, *args, **kwargs):
        self.quantity = Decimal(str(self.quantity))
        self.unit_price = Decimal(str(self.unit_price))
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product} - {self.quantity}"
