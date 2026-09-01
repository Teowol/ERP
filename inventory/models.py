from django.db import models

# Create your models here.

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class ProductCategory(models.Model):
    """Ürün kategorileri. Örneğin: Ham Madde, Yarı Mamul, Bitmiş Ürün."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Ürün Kategorisi"
        verbose_name_plural = "Ürün Kategorileri"

    def __str__(self):
        return self.name


class Product(models.Model):
    """Spor ayakkabı üretiminde kullanılan tüm maddeler."""

    class ProductType(models.TextChoices):
        RAW_MATERIAL = "raw_material", "Ham Madde"
        SEMI_FINISHED = "semi_finished", "Yarı Mamul"
        FINISHED_GOOD = "finished_good", "Bitmiş Ürün"
        PACKAGING = "packaging", "Ambalaj"
        CONSUMABLE = "consumable", "Sarf Malzemesi"

    class Unit(models.TextChoices):
        PIECE = "piece", "Adet"
        KG = "kg", "Kilogram"
        METER = "meter", "Metre"
        SQUARE_METER = "m2", "Metrekare"
        PAIR = "pair", "Çift"
        LITER = "liter", "Litre"
        ROLL = "roll", "Rulo"

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
    )
    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        default=ProductType.RAW_MATERIAL,
    )
    unit = models.CharField(
        max_length=20,
        choices=Unit.choices,
        default=Unit.KG,
    )
    minimum_stock_level = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Ürün"
        verbose_name_plural = "Ürünler"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Warehouse(models.Model):
    """Depolar. Örneğin: Ham Madde Deposu, Yarı Mamul Deposu, Mamul Deposu."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Depo"
        verbose_name_plural = "Depolar"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Lot(models.Model):
    """Ürün lot / parti takibi. Üretimden çıkan veya satın alınan her parti
    için benzersiz bir lot numarası tutulur."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Aktif"
        QUARANTINED = "quarantined", "Karantinada"
        CONSUMED = "consumed", "Tükendi"
        EXPIRED = "expired", "Süresi Doldu"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="lots",
        verbose_name="Ürün",
    )
    lot_number = models.CharField(
        max_length=60,
        unique=True,
        verbose_name="Lot Numarası",
    )
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Lotun oluştuğu kayıt türü. Örneğin: ProductionOrder, PurchaseOrder.",
        verbose_name="Referans Türü",
    )
    reference_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name="Referans ID",
    )
    manufactured_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Üretim Tarihi",
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Son Kullanma Tarihi",
    )
    initial_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Başlangıç Miktarı",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Durum",
    )
    note = models.TextField(blank=True, verbose_name="Not")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lot"
        verbose_name_plural = "Lotlar"

    @property
    def remaining_quantity(self):
        """Bu lottan hâlâ stokta kalan net miktar (giriş - çıkış)."""
        in_qty = self.stock_movements.filter(
            movement_type=StockMovement.MovementType.IN
        ).aggregate(total=models.Sum("quantity"))["total"] or Decimal("0")
        out_qty = self.stock_movements.filter(
            movement_type=StockMovement.MovementType.OUT
        ).aggregate(total=models.Sum("quantity"))["total"] or Decimal("0")
        return in_qty - out_qty

    def __str__(self):
        return f"{self.lot_number} ({self.product.code})"


class Stock(models.Model):
    """Ürünün depodaki mevcut, ayrılmış ve kullanılabilir miktarı."""

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    reserved_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"],
                name="unique_product_warehouse_stock",
            ),
        ]
        ordering = ["product", "warehouse"]
        verbose_name = "Stok"
        verbose_name_plural = "Stoklar"

    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity

    def __str__(self):
        return f"{self.product} - {self.warehouse}"


class StockMovement(models.Model):
    """Stok hareketleri. Giriş, çıkış, düzeltme, depolar arası transfer."""

    class MovementType(models.TextChoices):
        IN = "in", "Giriş"
        OUT = "out", "Çıkış"
        ADJUSTMENT = "adjustment", "Düzeltme"
        TRANSFER = "transfer", "Transfer"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    lot = models.ForeignKey(
        "Lot",
        on_delete=models.PROTECT,
        related_name="stock_movements",
        null=True,
        blank=True,
        verbose_name="Lot",
        help_text="Bu hareketin ilişkili olduğu lot (varsa).",
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="İlişkili olduğu kayıt türü. Örneğin: PurchaseOrder, ProductionOrder, Shipment.",
    )
    reference_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="İlişkili kaydın ID'si.",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Stok Hareketi"
        verbose_name_plural = "Stok Hareketleri"

    def __str__(self):
        return f"{self.product} - {self.movement_type} - {self.quantity}"