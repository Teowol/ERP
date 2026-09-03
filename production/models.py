from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import get_language

from inventory.models import Product


class ProductionLine(models.Model):
    """Fabrikadaki üretim hatları."""

    code = models.CharField(max_length=30, unique=True, verbose_name="Hat Kodu")
    name = models.CharField(max_length=150, verbose_name="Hat Adı")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    capacity_per_day = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Günlük Kapasite",
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
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

    code = models.CharField(max_length=30, unique=True, verbose_name="İş Merkezi Kodu")
    name = models.CharField(max_length=150, verbose_name="İş Merkezi Adı")
    production_line = models.ForeignKey(
        ProductionLine,
        on_delete=models.PROTECT,
        related_name="work_centers",
        verbose_name="Üretim Hattı",
    )
    machine_name = models.CharField(max_length=150, blank=True, verbose_name="Makine Adı")
    capacity_per_hour = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Saatlik Kapasite",
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
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
    name = models.CharField(max_length=150, verbose_name="Rota Adı")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Durum",
    )
    description = models.TextField(blank=True, verbose_name="Açıklama")
    valid_from = models.DateField(null=True, blank=True, verbose_name="Geçerlilik Başlangıcı")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Geçerlilik Bitişi")
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
    name = models.CharField(max_length=150, verbose_name="Operasyon Adı")
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
    description = models.TextField(blank=True, verbose_name="Açıklama")

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
    name = models.CharField(max_length=150, verbose_name="Reçete Adı")
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
    description = models.TextField(blank=True, verbose_name="Açıklama")
    valid_from = models.DateField(null=True, blank=True, verbose_name="Geçerlilik Başlangıcı")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Geçerlilik Bitişi")
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
    description = models.TextField(blank=True, verbose_name="Açıklama")

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


class ProductionOrder(models.Model):
    """Üretim Emri (İş Emri)."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Planlandı"
        RELEASED = "released", "Serbest Bırakıldı / Başlatılabilir"
        IN_PROGRESS = "in_progress", "Üretimde"
        QUALITY_CHECK = "quality_check", "Kalite Kontrolde"
        COMPLETED = "completed", "Tamamlandı"
        CANCELLED = "cancelled", "İptal Edildi"

    class Priority(models.TextChoices):
        LOW = "low", "Düşük"
        MEDIUM = "medium", "Normal"
        HIGH = "high", "Yüksek"
        URGENT = "urgent", "Acil"

    order_number = models.CharField(max_length=30, unique=True, verbose_name="Üretim Emri No")
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="production_orders",
        verbose_name="Üretilecek Ürün",
    )
    bill_of_material = models.ForeignKey(
        BillOfMaterial,
        on_delete=models.PROTECT,
        related_name="production_orders",
        verbose_name="Kullanılacak Reçete",
    )
    routing = models.ForeignKey(
        Routing,
        on_delete=models.PROTECT,
        related_name="production_orders",
        verbose_name="Kullanılacak Rota",
    )
    production_line = models.ForeignKey(
        ProductionLine,
        on_delete=models.PROTECT,
        related_name="production_orders",
        verbose_name="Üretim Hattı",
    )
    planned_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name="Planlanan Miktar",
    )
    produced_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Üretilen Miktar",
    )
    scrapped_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Fire Miktarı",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name="Durum",
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="Öncelik",
    )
    planned_start_date = models.DateTimeField(verbose_name="Planlanan Başlangıç")
    planned_end_date = models.DateTimeField(verbose_name="Planlanan Bitiş")
    actual_start_date = models.DateTimeField(null=True, blank=True, verbose_name="Gerçekleşen Başlangıç")
    actual_end_date = models.DateTimeField(null=True, blank=True, verbose_name="Gerçekleşen Bitiş")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_production_orders",
        verbose_name="Oluşturan",
    )
    raw_materials_warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="production_orders_raw",
        null=True,
        blank=True,
        verbose_name="Hammadde Deposu",
    )
    finished_goods_warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="production_orders_finished",
        null=True,
        blank=True,
        verbose_name="Mamul Deposu",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    reference_order_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Referans Sipariş No",
        help_text="Bu üretim emrinin bağlı olduğu satış siparişi numarası.",
    )

    class Meta:
        ordering = ["-planned_start_date", "-priority"]
        verbose_name = "Üretim Emri"
        verbose_name_plural = "Üretim Emirleri"

    @transaction.atomic
    def create_operations_from_routing(self):
        """Rotadaki operasyonları üretim emri operasyonlarına dönüştürür."""
        if not self.routing:
            raise ValueError("Rota tanımlı değil.")
        if self.order_operations.exists():
            return
        for routing_op in self.routing.operations.all():
            ProductionOrderOperation.objects.create(
                production_order=self,
                routing_operation=routing_op,
                status=ProductionOrderOperation.Status.PENDING,
            )

    @transaction.atomic
    def create_components_from_bom(self):
        """Reçeteden üretim emri hammadde kalemlerini otomatik oluşturur."""
        if not self.bill_of_material:
            raise ValueError("Reçete tanımlı değil.")
        if self.order_components.exists():
            return
        ratio = self.planned_quantity / self.bill_of_material.output_quantity
        for item in self.bill_of_material.items.all():
            required = (item.quantity * ratio) * (
                Decimal("1") + item.scrap_percentage / Decimal("100")
            )
            ProductionOrderComponent.objects.create(
                production_order=self,
                component=item.component,
                required_quantity=required,
                consumed_quantity=Decimal("0"),
                is_fully_consumed=False,
            )

    @transaction.atomic
    def consume_materials(self, user=None):
        """Planlanan hammadde miktarlarını stoktan çıkarır."""
        StockMovement = apps.get_model("inventory", "StockMovement")
        if self.status not in [self.Status.RELEASED, self.Status.IN_PROGRESS]:
            raise ValueError(
                "Malzeme tüketimi için emir 'Serbest Bırakıldı' veya 'Üretimde' durumunda olmalı."
            )
        if not self.raw_materials_warehouse:
            raise ValueError("Hammadde deposu seçilmemiş.")
        if not self.order_components.exists():
            self.create_components_from_bom()
        for component in self.order_components.all():
            if component.is_fully_consumed:
                continue
            StockMovement.objects.create(
                product=component.component,
                warehouse=self.raw_materials_warehouse,
                movement_type=StockMovement.MovementType.OUT,
                quantity=component.required_quantity,
                reference_type="production_order",
                reference_id=self.pk,
                note=f"Üretim emri {self.order_number} malzeme tüketimi",
            )
            self._update_stock(
                component.component,
                self.raw_materials_warehouse,
                -component.required_quantity,
            )
            component.consumed_quantity = component.required_quantity
            component.is_fully_consumed = True
            component.save(
                update_fields=["consumed_quantity", "is_fully_consumed"]
            )

    @transaction.atomic
    def complete_production(self, user=None):
        """Üretimi tamamlar; lot oluşturur, mamul girişini ve kalan malzeme
        tüketimini bu lot üzerinden yapar."""
        StockMovement = apps.get_model("inventory", "StockMovement")
        Lot = apps.get_model("inventory", "Lot")
        if self.status not in [self.Status.IN_PROGRESS, self.Status.QUALITY_CHECK]:
            raise ValueError(
                "Üretim tamamlanabilmesi için emir 'Üretimde' veya 'Kalite Kontrolde' olmalı."
            )
        if not self.finished_goods_warehouse:
            raise ValueError("Mamul deposu seçilmemiş.")
        if self.order_components.filter(is_fully_consumed=False).exists():
            self.consume_materials(user=user)
        self.status = self.Status.COMPLETED
        self.produced_quantity = self.planned_quantity
        self.actual_end_date = timezone.now()
        self.save(
            update_fields=[
                "status",
                "produced_quantity",
                "actual_end_date",
                "updated_at",
            ]
        )

        lot = Lot.objects.create(
            product=self.product,
            lot_number=f"LOT-{self.order_number}",
            reference_type="production_order",
            reference_id=self.pk,
            manufactured_date=timezone.now().date(),
            initial_quantity=self.produced_quantity,
            status=Lot.Status.ACTIVE,
            note=f"Üretim emri {self.order_number} çıktısı.",
        )

        StockMovement.objects.create(
            product=self.product,
            warehouse=self.finished_goods_warehouse,
            lot=lot,
            movement_type=StockMovement.MovementType.IN,
            quantity=self.produced_quantity,
            reference_type="production_order",
            reference_id=self.pk,
            note=f"Üretim emri {self.order_number} mamul girişi",
        )
        self._update_stock(
            self.product,
            self.finished_goods_warehouse,
            self.produced_quantity,
        )

        if self.reference_order_number:
            from distribution.tasks import ship_fulfilled_production_task
            po_pk = self.pk
            user_id = user.pk if user else None
            transaction.on_commit(
                lambda language_code=get_language(): ship_fulfilled_production_task.delay(po_pk, user_id, language_code)
            )

        lot = Lot.objects.filter(
            reference_type="production_order",
            reference_id=self.pk,
        ).order_by("-created_at").first()
        ProductionCost.calculate_for_order(
            self,
            user=user,
            lot=lot,
            raw_material_cost_override=Decimal("0"),
            labor_cost_override=Decimal("0"),
            machine_cost_override=Decimal("0"),
            overhead_cost_override=Decimal("0"),
            scrap_quantity_override=self.scrapped_quantity,
        )

    def _update_stock(self, product, warehouse, quantity_delta):
        Stock = apps.get_model("inventory", "Stock")
        stock, _ = Stock.objects.select_for_update().get_or_create(
            product=product,
            warehouse=warehouse,
            defaults={
                "quantity": Decimal("0"),
                "reserved_quantity": Decimal("0"),
            },
        )
        stock.quantity += quantity_delta
        if stock.quantity < 0:
            raise ValueError(f"Stok yetersiz: {product} ({warehouse})")
        stock.save(update_fields=["quantity", "updated_at"])

    @transaction.atomic
    def release(self):
        if self.status != self.Status.PLANNED:
            raise ValueError("Sadece 'Planlandı' durumundaki emir serbest bırakılabilir.")
        self.status = self.Status.RELEASED
        self.save(update_fields=["status", "updated_at"])

    @transaction.atomic
    def start_production(self):
        if self.status != self.Status.RELEASED:
            raise ValueError("Sadece 'Serbest Bırakıldı' durumundaki emir başlatılabilir.")
        if not self.raw_materials_warehouse:
            raise ValueError("Hammadde deposu seçilmemiş.")
        self.status = self.Status.IN_PROGRESS
        self.actual_start_date = timezone.now()
        self.save(update_fields=["status", "actual_start_date", "updated_at"])

    @transaction.atomic
    def send_to_quality_check(self):
        if self.status != self.Status.IN_PROGRESS:
            raise ValueError("Sadece 'Üretimde' durumundaki emir kalite kontrole gönderilebilir.")
        self.status = self.Status.QUALITY_CHECK
        self.save(update_fields=["status", "updated_at"])

    @transaction.atomic
    def cancel(self):
        if self.status in [self.Status.COMPLETED, self.Status.CANCELLED]:
            raise ValueError("Tamamlanmış veya iptal edilmiş emir tekrar iptal edilemez.")
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])

    def __str__(self):
        return f"{self.order_number} - {self.product.name} ({self.planned_quantity} Adet)"


class ProductionCost(models.Model):
    """Üretim emri bazlı maliyet takibi."""

    production_order = models.OneToOneField(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name="production_cost",
        verbose_name="Üretim Emri",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="production_costs",
        verbose_name="Ürün",
    )
    lot = models.ForeignKey(
        "inventory.Lot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="production_costs",
        verbose_name="Lot",
    )
    raw_material_cost = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Hammadde Maliyeti",
    )
    labor_cost = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="İşçilik Maliyeti",
    )
    machine_cost = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Makine / Operasyon Maliyeti",
    )
    overhead_cost = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Genel Üretim Gideri",
    )
    scrap_cost = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Fire Maliyeti",
    )
    total_cost = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Toplam Maliyet",
    )
    produced_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Sağlam Üretim Miktarı",
    )
    scrap_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Fire Miktarı",
    )
    unit_cost = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Birim Maliyet",
    )
    calculation_date = models.DateTimeField(default=timezone.now, verbose_name="Hesaplama Tarihi")
    creation_source = models.CharField(
        max_length=40,
        default="manual",
        choices=[("manual", "Manuel"), ("auto", "Otomatik")],
        verbose_name="Hesaplama Kaynağı",
    )
    calculation_version = models.PositiveIntegerField(default=1, verbose_name="Hesaplama Versiyonu")
    calculation_note = models.TextField(blank=True, verbose_name="Hesaplama Notu")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_costs",
        null=True,
        blank=True,
        verbose_name="Oluşturan / Güncelleyen",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-calculation_date", "-pk"]
        verbose_name = "Üretim Maliyeti"
        verbose_name_plural = "Üretim Maliyetleri"

    def clean(self):
        for field_name in [
            "raw_material_cost",
            "labor_cost",
            "machine_cost",
            "overhead_cost",
            "scrap_cost",
            "total_cost",
            "produced_quantity",
            "scrap_quantity",
            "unit_cost",
        ]:
            value = getattr(self, field_name)
            if value < Decimal("0"):
                raise ValueError(f"{field_name} negatif olamaz.")
        if self.scrap_quantity > self.produced_quantity and self.produced_quantity > Decimal("0"):
            raise ValueError("Fire miktarı, sağlam üretim miktarını aşamaz.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    @transaction.atomic
    def calculate_for_order(
        cls,
        production_order,
        user=None,
        lot=None,
        raw_material_cost_override=None,
        labor_cost_override=None,
        machine_cost_override=None,
        overhead_cost_override=None,
        scrap_quantity_override=None,
        force=False,
    ):
        if production_order is None:
            raise ValueError("Maliyet hesaplaması için üretim emri gerekli.")

        raw_material_cost = (
            Decimal(str(raw_material_cost_override))
            if raw_material_cost_override is not None
            else Decimal("0")
        )
        labor_cost = (
            Decimal(str(labor_cost_override))
            if labor_cost_override is not None
            else Decimal("0")
        )
        machine_cost = (
            Decimal(str(machine_cost_override))
            if machine_cost_override is not None
            else Decimal("0")
        )
        overhead_cost = (
            Decimal(str(overhead_cost_override))
            if overhead_cost_override is not None
            else Decimal("0")
        )

        produced_quantity = production_order.produced_quantity if production_order.produced_quantity > Decimal("0") else Decimal("0")
        scrap_quantity = (
            Decimal(str(scrap_quantity_override))
            if scrap_quantity_override is not None
            else production_order.scrapped_quantity
        )
        if scrap_quantity < Decimal("0"):
            raise ValueError("Fire miktarı negatif olamaz.")

        if produced_quantity == Decimal("0") and production_order.planned_quantity > Decimal("0"):
            unit_basis = production_order.planned_quantity
        else:
            unit_basis = produced_quantity

        base_total = raw_material_cost + labor_cost + machine_cost + overhead_cost

        if scrap_quantity > Decimal("0"):
            if unit_basis > Decimal("0"):
                scrap_cost = (base_total / unit_basis) * scrap_quantity
            else:
                scrap_cost = Decimal("0")
        else:
            scrap_cost = Decimal("0")

        total_cost = base_total + scrap_cost
        if produced_quantity > Decimal("0"):
            unit_cost = total_cost / produced_quantity
        else:
            unit_cost = Decimal("0")

        note_parts = []
        if raw_material_cost == Decimal("0"):
            note_parts.append(
                "Hammadde birim maliyeti sistemde tutulmadığı için hesaplama güvenli varsayılan olarak 0 alındı. "
                "Gerçek maliyetleri manuel girmek gerekir."
            )
        if scrap_quantity > Decimal("0"):
            note_parts.append(
                f"Fire maliyeti {scrap_quantity} adet üzerinden hesaplandı."
            )
        if produced_quantity == Decimal("0"):
            note_parts.append(
                "Sağlam üretim miktarı sıfır olduğu için birim maliyet 0 olarak bırakıldı."
            )

        cost_record, created = cls.objects.select_for_update().get_or_create(
            production_order=production_order,
            defaults={
                "product": production_order.product,
                "lot": lot,
                "raw_material_cost": raw_material_cost,
                "labor_cost": labor_cost,
                "machine_cost": machine_cost,
                "overhead_cost": overhead_cost,
                "scrap_cost": scrap_cost,
                "total_cost": total_cost,
                "produced_quantity": produced_quantity,
                "scrap_quantity": scrap_quantity,
                "unit_cost": unit_cost,
                "calculation_date": timezone.now(),
                "created_by": user,
                "creation_source": "auto" if user is None else "manual",
                "calculation_note": "; ".join(note_parts),
            },
        )

        if not created:
            if force:
                cost_record.calculation_version += 1
            cost_record.product = production_order.product
            cost_record.lot = lot or cost_record.lot
            cost_record.raw_material_cost = raw_material_cost
            cost_record.labor_cost = labor_cost
            cost_record.machine_cost = machine_cost
            cost_record.overhead_cost = overhead_cost
            cost_record.scrap_cost = scrap_cost
            cost_record.total_cost = total_cost
            cost_record.produced_quantity = produced_quantity
            cost_record.scrap_quantity = scrap_quantity
            cost_record.unit_cost = unit_cost
            cost_record.calculation_date = timezone.now()
            cost_record.created_by = user or cost_record.created_by
            cost_record.creation_source = "auto" if user is None else "manual"
            patch_note = "; ".join(note_parts) if note_parts else cost_record.calculation_note
            if patch_note:
                cost_record.calculation_note = patch_note
            cost_record.save(update_fields=[
                "product",
                "lot",
                "raw_material_cost",
                "labor_cost",
                "machine_cost",
                "overhead_cost",
                "scrap_cost",
                "total_cost",
                "produced_quantity",
                "scrap_quantity",
                "unit_cost",
                "calculation_date",
                "created_by",
                "creation_source",
                "calculation_note",
                "updated_at",
            ])
            if force:
                cost_record.save(update_fields=["calculation_version", "updated_at"])
            return cost_record

        if created:
            cost_record.calculation_version = 1
            cost_record.save(update_fields=["calculation_version", "updated_at"])
        return cost_record

    def __str__(self):
        return f"{self.production_order.order_number} - Toplam {self.total_cost}"


class ProductionOrderOperation(models.Model):
    """Üretim emri içerisindeki operasyonel aşamaların takibi."""

    class Status(models.TextChoices):
        PENDING = "pending", "Bekliyor"
        IN_PROGRESS = "in_progress", "İşlemde"
        COMPLETED = "completed", "Tamamlandı"
        PAUSED = "paused", "Duraklatıldı"

    production_order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name="order_operations",
        verbose_name="Üretim Emri",
    )
    routing_operation = models.ForeignKey(
        RoutingOperation,
        on_delete=models.PROTECT,
        related_name="order_operations",
        verbose_name="Rota Operasyonu",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Durum",
    )
    completed_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        verbose_name="Tamamlanan Miktar",
    )
    actual_start_time = models.DateTimeField(null=True, blank=True, verbose_name="Başlama Zamanı")
    actual_end_time = models.DateTimeField(null=True, blank=True, verbose_name="Bitiş Zamanı")
    operator_notes = models.TextField(blank=True, verbose_name="Operatör Notları")

    class Meta:
        ordering = ["production_order", "routing_operation__sequence"]
        verbose_name = "Üretim Emri Operasyonu"
        verbose_name_plural = "Üretim Emri Operasyonları"

    @transaction.atomic
    def start(self, user=None):
        if self.status not in [self.Status.PENDING, self.Status.PAUSED]:
            raise ValueError("Operasyon 'Bekliyor' veya 'Duraklatıldı' durumunda ise başlatılabilir.")
        self.status = self.Status.IN_PROGRESS
        if not self.actual_start_time:
            self.actual_start_time = timezone.now()
        self.save(update_fields=["status", "actual_start_time"])

    @transaction.atomic
    def pause(self, user=None):
        if self.status != self.Status.IN_PROGRESS:
            raise ValueError("Sadece 'İşlemde' durumundaki operasyon duraklatılabilir.")
        self.status = self.Status.PAUSED
        self.save(update_fields=["status"])

    @transaction.atomic
    def complete(self, completed_quantity, user=None):
        if self.status != self.Status.IN_PROGRESS:
            raise ValueError("Sadece 'İşlemde' durumundaki operasyon tamamlanabilir.")
        if completed_quantity < 0:
            raise ValueError("Tamamlanan miktar negatif olamaz.")
        self.status = self.Status.COMPLETED
        self.completed_quantity = completed_quantity
        self.actual_end_time = timezone.now()
        self.save(update_fields=["status", "completed_quantity", "actual_end_time"])

    def __str__(self):
        return f"{self.production_order.order_number} - {self.routing_operation.name}"


class ProductionOrderComponent(models.Model):
    """Üretim emrinde tüketilecek planlanan ve gerçekleşen hammadde miktarları."""

    production_order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name="order_components",
        verbose_name="Üretim Emri",
    )
    component = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="production_requirements",
        verbose_name="Hammadde / Yarı Mamul",
    )
    required_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
        verbose_name="Gereken Miktar",
    )
    consumed_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=Decimal("0"),
        verbose_name="Tüketilen Miktar",
    )
    is_fully_consumed = models.BooleanField(
        default=False,
        verbose_name="Tamamı Tüketildi mi?",
    )

    class Meta:
        verbose_name = "Üretim Emri Hammaddesi"
        verbose_name_plural = "Üretim Emri Hammaddeleri"

    def __str__(self):
        return f"{self.production_order.order_number} - {self.component.name}"