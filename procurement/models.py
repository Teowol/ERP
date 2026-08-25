from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from inventory.models import Product, Warehouse


class Supplier(models.Model):
    """Kauçuk, kumaş, iplik ve diğer malzemeleri sağlayan tedarikçiler."""

    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Tedarikçi Kodu",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Firma Adı",
    )
    tax_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Vergi Numarası",
    )
    contact_person = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Yetkili Kişi",
    )
    email = models.EmailField(
        blank=True,
        verbose_name="E-posta",
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Telefon",
    )
    address = models.TextField(
        blank=True,
        verbose_name="Adres",
    )
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ödeme Koşulları",
    )
    delivery_lead_time_days = models.PositiveIntegerField(
        default=0,
        verbose_name="Standart Teslim Süresi (Gün)",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif mi?",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Tedarikçi"
        verbose_name_plural = "Tedarikçiler"

    def __str__(self):
        return f"{self.code} - {self.name}"


class SupplierProduct(models.Model):
    """Bir tedarikçinin sağlayabildiği ürün ve fiyat bilgileri."""

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="supplier_products",
        verbose_name="Tedarikçi",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="supplier_products",
        verbose_name="Ürün",
    )
    supplier_product_code = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Tedarikçi Ürün Kodu",
    )
    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Birim Fiyat",
    )
    currency = models.CharField(
        max_length=3,
        default="TRY",
        verbose_name="Para Birimi",
    )
    minimum_order_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Minimum Sipariş Miktarı",
    )
    lead_time_days = models.PositiveIntegerField(
        default=0,
        verbose_name="Teslim Süresi (Gün)",
    )
    is_preferred = models.BooleanField(
        default=False,
        verbose_name="Tercih Edilen Tedarikçi mi?",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif mi?",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "product"],
                name="unique_supplier_product",
            )
        ]
        ordering = ["supplier", "product"]
        verbose_name = "Tedarikçi Ürünü"
        verbose_name_plural = "Tedarikçi Ürünleri"

    def __str__(self):
        return f"{self.supplier} - {self.product}"


class PurchaseRequest(models.Model):
    """Departmanların oluşturduğu satın alma talepleri."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Taslak"
        SUBMITTED = "submitted", "Gönderildi"
        APPROVED = "approved", "Onaylandı"
        REJECTED = "rejected", "Reddedildi"
        ORDERED = "ordered", "Siparişe Dönüştü"
        COMPLETED = "completed", "Tamamlandı"
        CANCELLED = "cancelled", "İptal Edildi"

    request_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Talep Numarası",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_requests",
        verbose_name="Talep Eden",
    )
    request_date = models.DateField(
        auto_now_add=True,
        verbose_name="Talep Tarihi",
    )
    required_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Gerekli Tarih",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Durum",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Açıklama",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Satın Alma Talebi"
        verbose_name_plural = "Satın Alma Talepleri"

    def __str__(self):
        return self.request_number


class PurchaseRequestItem(models.Model):
    """Satın alma talebindeki ürün ve miktar bilgisi."""

    purchase_request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Satın Alma Talebi",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="purchase_request_items",
        verbose_name="Ürün",
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name="Miktar",
    )
    reason = models.TextField(
        blank=True,
        verbose_name="Talep Gerekçesi",
    )

    class Meta:
        verbose_name = "Satın Alma Talep Kalemi"
        verbose_name_plural = "Satın Alma Talep Kalemleri"

    def __str__(self):
        return f"{self.purchase_request} - {self.product}"


class PurchaseOrder(models.Model):
    """Tedarikçiye gönderilen satın alma siparişi."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Taslak"
        SENT = "sent", "Gönderildi"
        CONFIRMED = "confirmed", "Onaylandı"
        PARTIALLY_RECEIVED = "partially_received", "Kısmen Teslim Alındı"
        RECEIVED = "received", "Tamamı Teslim Alındı"
        CANCELLED = "cancelled", "İptal Edildi"

    order_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Sipariş Numarası",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        verbose_name="Tedarikçi",
    )
    purchase_request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_orders",
        verbose_name="Bağlı Satın Alma Talebi",
    )
    order_date = models.DateField(
        auto_now_add=True,
        verbose_name="Sipariş Tarihi",
    )
    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Beklenen Teslim Tarihi",
    )
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Durum",
    )
    currency = models.CharField(
        max_length=3,
        default="TRY",
        verbose_name="Para Birimi",
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Toplam Tutar",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Açıklama",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Satın Alma Siparişi"
        verbose_name_plural = "Satın Alma Siparişleri"

    def __str__(self):
        return self.order_number


class PurchaseOrderItem(models.Model):
    """Satın alma siparişinin ürün satırı."""

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Satın Alma Siparişi",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="purchase_order_items",
        verbose_name="Ürün",
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name="Sipariş Miktarı",
    )
    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Birim Fiyat",
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("20"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="KDV Oranı (%)",
    )
    received_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Teslim Alınan Miktar",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["purchase_order", "product"],
                name="unique_purchase_order_product",
            )
        ]
        verbose_name = "Satın Alma Sipariş Kalemi"
        verbose_name_plural = "Satın Alma Sipariş Kalemleri"

    def __str__(self):
        return f"{self.purchase_order} - {self.product}"


class GoodsReceipt(models.Model):
    """Tedarikçiden gelen malzemelerin fabrikaya kabul kaydı."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Taslak"
        RECEIVED = "received", "Teslim Alındı"
        INSPECTION = "inspection", "Kalite Kontrol Bekliyor"
        ACCEPTED = "accepted", "Kabul Edildi"
        PARTIALLY_ACCEPTED = "partially_accepted", "Kısmen Kabul Edildi"
        REJECTED = "rejected", "Reddedildi"

    receipt_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Mal Kabul Numarası",
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name="goods_receipts",
        verbose_name="Satın Alma Siparişi",
    )
    received_date = models.DateField(
        auto_now_add=True,
        verbose_name="Teslim Tarihi",
    )
    delivered_by = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Teslim Eden",
    )
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Durum",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Açıklama",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Mal Kabul"
        verbose_name_plural = "Mal Kabuller"

    def __str__(self):
        return self.receipt_number


class GoodsReceiptItem(models.Model):
    """Mal kabul içindeki ürün, miktar, lot ve depo bilgisi."""

    goods_receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Mal Kabul",
    )
    purchase_order_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.PROTECT,
        related_name="goods_receipt_items",
        verbose_name="Sipariş Kalemi",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="goods_receipt_items",
        verbose_name="Ürün",
    )
    received_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name="Gelen Miktar",
    )
    accepted_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Kabul Edilen Miktar",
    )
    rejected_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Reddedilen Miktar",
    )
    lot_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Lot Numarası",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="goods_receipt_items",
        verbose_name="Hedef Depo",
    )
    note = models.TextField(
        blank=True,
        verbose_name="Not",
    )

    class Meta:
        verbose_name = "Mal Kabul Kalemi"
        verbose_name_plural = "Mal Kabul Kalemleri"

    def __str__(self):
        return f"{self.goods_receipt} - {self.product}"