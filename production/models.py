from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from inventory.models import Product


class ProductionLine(models.Model):
    """Fabrikadaki üretim hatları."""

    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Hat Kodu",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Hat Adı",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Açıklama",
    )
    capacity_per_day = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Günlük Kapasite",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif mi?",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Üretim Hattı"
        verbose_name_plural = "Üretim Hatları"

    def __str__(self):
        return f"{self.code} - {self.name}"


class WorkCenter(models.Model):
    """Üretim hattı üzerindeki makine veya iş istasyonu."""

    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="İş Merkezi Kodu",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="İş Merkezi Adı",
    )
    production_line = models.ForeignKey(
        ProductionLine,
        on_delete=models.PROTECT,
        related_name="work_centers",
        verbose_name="Üretim Hattı",
    )
    machine_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Makine Adı",
    )
    capacity_per_hour = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Saatlik Kapasite",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif mi?",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "İş Merkezi"
        verbose_name_plural = "İş Merkezleri"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Routing(models.Model):
    """Bir ürünün hangi üretim adımlarından geçeceğini tanımlar."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Taslak"
        ACTIVE = "active", "Aktif"
        INACTIVE = "inactive", "Pasif"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="routings",
        verbose_name="Ürün",
    )
    version = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Versiyon",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Rota Adı",
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
    valid_from = models.DateField(
        null=True,
        blank=True,
        verbose_name="Geçerlilik Başlangıcı",
    )
    valid_until = models.DateField(
        null=True,
        blank=True,
        verbose_name="Geçerlilik Bitişi",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "version"],
                name="unique_product_routing_version",
            )
        ]
        ordering = ["product", "-version"]
        verbose_name = "Üretim Rotası"
        verbose_name_plural = "Üretim Rotaları"

    def __str__(self):
        return f"{self.product} - Rota v{self.version}"


class RoutingOperation(models.Model):
    """Üretim rotasındaki sıralı operasyon."""

    routing = models.ForeignKey(
        Routing,
        on_delete=models.CASCADE,
        related_name="operations",
        verbose_name="Üretim Rotası",
    )
    sequence = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Sıra",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Operasyon Adı",
    )
    work_center = models.ForeignKey(
        WorkCenter,
        on_delete=models.PROTECT,
        related_name="routing_operations",
        verbose_name="İş Merkezi",
    )
    setup_time_minutes = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Hazırlık Süresi (Dakika)",
    )
    cycle_time_minutes = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Çevrim Süresi (Dakika)",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Açıklama",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["routing", "sequence"],
                name="unique_routing_operation_sequence",
            )
        ]
        ordering = ["routing", "sequence"]
        verbose_name = "Rota Operasyonu"
        verbose_name_plural = "Rota Operasyonları"

    def __str__(self):
        return f"{self.routing} - {self.sequence}. {self.name}"


class BillOfMaterial(models.Model):
    """Ürünün üretiminde kullanılan malzeme reçetesi."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Taslak"
        ACTIVE = "active", "Aktif"
        INACTIVE = "inactive", "Pasif"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="bills_of_material",
        verbose_name="Üretilecek Ürün",
    )
    version = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Reçete Versiyonu",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Reçete Adı",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Durum",
    )
    output_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name="Üretim Çıktı Miktarı",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Açıklama",
    )
    valid_from = models.DateField(
        null=True,
        blank=True,
        verbose_name="Geçerlilik Başlangıcı",
    )
    valid_until = models.DateField(
        null=True,
        blank=True,
        verbose_name="Geçerlilik Bitişi",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "version"],
                name="unique_product_bom_version",
            )
        ]
        ordering = ["product", "-version"]
        verbose_name = "Ürün Reçetesi"
        verbose_name_plural = "Ürün Reçeteleri"

    def __str__(self):
        return f"{self.product} - Reçete v{self.version}"


class BOMItem(models.Model):
    """Ürün reçetesindeki tek bir malzeme veya yarı mamul."""

    bill_of_material = models.ForeignKey(
        BillOfMaterial,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Ürün Reçetesi",
    )
    component = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="bom_items",
        verbose_name="Bileşen",
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        validators=[MinValueValidator(Decimal("0.000001"))],
        verbose_name="Miktar",
    )
    scrap_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Fire Oranı (%)",
    )
    operation_sequence = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name="Kullanıldığı Operasyon Sırası",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Açıklama",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bill_of_material", "component"],
                name="unique_bom_component",
            )
        ]
        ordering = ["bill_of_material", "operation_sequence", "component"]
        verbose_name = "Reçete Kalemi"
        verbose_name_plural = "Reçete Kalemleri"

    def __str__(self):
        return f"{self.bill_of_material} - {self.component}"