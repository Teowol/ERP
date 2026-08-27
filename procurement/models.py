from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from inventory.models import Product


class Supplier(models.Model):
    """Bitmiş ürün tedarikçisi bilgileri."""

    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Tedarikçi Kodu",
    )
    company_name = models.CharField(
        max_length=200,
        verbose_name="Firma Unvanı",
    )
    commercial_title = models.CharField(
        max_length=250,
        blank=True,
        verbose_name="Ticari Unvan",
    )
    contact_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Yetkili Kişi",
    )
    contact_title = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Yetkili Ünvanı",
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Telefon",
    )
    mobile_phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Cep Telefonu",
    )
    email = models.EmailField(
        blank=True,
        verbose_name="E-posta",
    )
    website = models.URLField(
        blank=True,
        verbose_name="Web Sitesi",
    )
    tax_office = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Vergi Dairesi",
    )
    tax_number = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Vergi Numarası / TCKN",
    )
    mersis_number = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="MERSİS Numarası",
    )
    address = models.TextField(
        blank=True,
        verbose_name="Adres",
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="İl",
    )
    district = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="İlçe",
    )
    country = models.CharField(
        max_length=100,
        default="Türkiye",
        verbose_name="Ülke",
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Posta Kodu",
    )
    payment_term_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Ödeme Vadesi (Gün)",
    )
    currency = models.CharField(
        max_length=3,
        default="TRY",
        verbose_name="Varsayılan Para Birimi",
    )
    bank_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Banka Adı",
    )
    iban = models.CharField(
        max_length=34,
        blank=True,
        verbose_name="IBAN",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notlar",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif mi?",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Oluşturulma Tarihi",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Güncellenme Tarihi",
    )

    class Meta:
        ordering = ["code"]
        verbose_name = "Tedarikçi"
        verbose_name_plural = "Tedarikçiler"

    def __str__(self):
        return f"{self.code} - {self.company_name}"


class PurchaseRequest(models.Model):
    """Alıcı tarafından oluşturulan veya stok kontrolüyle açılan satın alma talebi."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Taslak"
        PENDING_APPROVAL = "pending_approval", "Onay Bekliyor"
        APPROVED = "approved", "Onaylandı"
        REJECTED = "rejected", "Reddedildi"
        CONVERTED = "converted", "Siparişe Dönüştü"
        CANCELLED = "cancelled", "İptal"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manuel"
        STOCK_ALERT = "stock_alert", "Otomatik Stok Uyarısı"

    request_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Talep Numarası",
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
        verbose_name="Talep Kaynağı",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Durum",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_requests_created",
        verbose_name="Talebi Oluşturan",
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Talep Tarihi",
    )
    required_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="İhtiyaç Tarihi",
    )
    purpose = models.TextField(
        blank=True,
        verbose_name="Talep Açıklaması",
    )
    approval_note = models.TextField(
        blank=True,
        verbose_name="Onay / Red Notu",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_requests_approved",
        null=True,
        blank=True,
        verbose_name="Onaylayan Kullanıcı",
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Onay Tarihi",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Oluşturulma Tarihi",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Güncellenme Tarihi",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Satın Alma Talebi"
        verbose_name_plural = "Satın Alma Talepleri"

    def __str__(self):
        return self.request_number


class PurchaseRequestLine(models.Model):
    """Satın alma talebinin bitmiş ürün kalemleri."""

    purchase_request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name="lines",
        verbose_name="Satın Alma Talebi",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="purchase_request_lines",
        limit_choices_to={"product_type": Product.ProductType.FINISHED_GOOD},
        verbose_name="Bitmiş Ürün",
    )
    requested_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name="Talep Miktarı",
    )
    note = models.CharField(
        max_length=250,
        blank=True,
        verbose_name="Kalem Notu",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["purchase_request", "product"],
                name="unique_purchase_request_product",
            )
        ]
        ordering = ["id"]
        verbose_name = "Satın Alma Talep Kalemi"
        verbose_name_plural = "Satın Alma Talep Kalemleri"

    def clean(self):
        if self.product_id and self.product.product_type != Product.ProductType.FINISHED_GOOD:
            raise ValidationError(
                {"product": "Satın alma talebine yalnızca bitmiş ürün eklenebilir."}
            )

    def __str__(self):
        return f"{self.purchase_request.request_number} - {self.product}"


class PurchaseOrder(models.Model):
    """Onaylı satın alma talebinden oluşturulan tedarikçi siparişi."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Taslak"
        SENT = "sent", "Tedarikçiye Gönderildi"
        PARTIALLY_RECEIVED = "partially_received", "Kısmi Teslim Alındı"
        COMPLETED = "completed", "Tamamlandı"
        CANCELLED = "cancelled", "İptal"

    order_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Sipariş Numarası",
    )
    purchase_request = models.OneToOneField(
        PurchaseRequest,
        on_delete=models.PROTECT,
        related_name="purchase_order",
        verbose_name="Kaynak Satın Alma Talebi",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        verbose_name="Tedarikçi",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Durum",
    )
    order_date = models.DateField(
        verbose_name="Sipariş Tarihi",
    )
    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Beklenen Teslim Tarihi",
    )
    currency = models.CharField(
        max_length=3,
        default="TRY",
        verbose_name="Para Birimi",
    )
    payment_term_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Ödeme Vadesi (Gün)",
    )
    delivery_address = models.TextField(
        blank=True,
        verbose_name="Teslimat Adresi",
    )
    note = models.TextField(
        blank=True,
        verbose_name="Sipariş Notu",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_orders_created",
        null=True,
        blank=True,
        verbose_name="Siparişi Oluşturan",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Oluşturulma Tarihi",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Güncellenme Tarihi",
    )

    class Meta:
        ordering = ["-order_date", "-id"]
        verbose_name = "Satın Alma Siparişi"
        verbose_name_plural = "Satın Alma Siparişleri"

    def clean(self):
        if (
            self.purchase_request_id
            and self.purchase_request.status != PurchaseRequest.Status.APPROVED
        ):
            raise ValidationError(
                {
                    "purchase_request": (
                        "Sipariş yalnızca onaylanmış bir satın alma talebinden oluşturulabilir."
                    )
                }
            )

    def __str__(self):
        return self.order_number


class PurchaseOrderLine(models.Model):
    """Tedarikçiye verilen bitmiş ürün sipariş kalemleri."""

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="lines",
        verbose_name="Satın Alma Siparişi",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="purchase_order_lines",
        limit_choices_to={"product_type": Product.ProductType.FINISHED_GOOD},
        verbose_name="Bitmiş Ürün",
    )
    ordered_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name="Sipariş Miktarı",
    )
    received_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Teslim Alınan Miktar",
    )
    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Birim Fiyat",
    )
    note = models.CharField(
        max_length=250,
        blank=True,
        verbose_name="Kalem Notu",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["purchase_order", "product"],
                name="unique_purchase_order_product",
            )
        ]
        ordering = ["id"]
        verbose_name = "Satın Alma Sipariş Kalemi"
        verbose_name_plural = "Satın Alma Sipariş Kalemleri"

    def clean(self):
        errors = {}

        if self.product_id and self.product.product_type != Product.ProductType.FINISHED_GOOD:
            errors["product"] = "Satın alma siparişine yalnızca bitmiş ürün eklenebilir."

        if self.received_quantity > self.ordered_quantity:
            errors["received_quantity"] = (
                "Teslim alınan miktar sipariş miktarından büyük olamaz."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def line_total(self):
        return self.ordered_quantity * self.unit_price

    def __str__(self):
        return f"{self.purchase_order.order_number} - {self.product}"