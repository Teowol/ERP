from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


def validate_purchase_order_links(apps, schema_editor):
    PurchaseOrder = apps.get_model("procurement", "PurchaseOrder")
    null_order = PurchaseOrder.objects.filter(purchase_request__isnull=True).first()
    if null_order:
        raise RuntimeError(
            "Satın alma siparişi %s bir satın alma talebine bağlı değil. "
            "OneToOne dönüşümünden önce bu kaydı ilişkilendirin." % null_order.order_number
        )
    duplicate = (
        PurchaseOrder.objects.values("purchase_request_id")
        .annotate(total=models.Count("id"))
        .filter(total__gt=1)
        .order_by("purchase_request_id")
        .first()
    )
    if duplicate:
        raise RuntimeError(
            "Bir satın alma talebine birden fazla sipariş bağlı. "
            "Talep ID %s için kayıtları ayırın." % duplicate["purchase_request_id"]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0001_initial"),
        ("procurement", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(validate_purchase_order_links, migrations.RunPython.noop),
        migrations.RenameField("supplier", "name", "company_name"),
        migrations.RenameField("supplier", "contact_person", "contact_name"),
        migrations.RenameField("purchaserequest", "description", "purpose"),
        migrations.RenameField("purchaserequest", "request_date", "requested_at"),
        migrations.RenameField("purchaseorder", "description", "note"),
        migrations.RenameModel("PurchaseRequestItem", "PurchaseRequestLine"),
        migrations.RenameField("purchaserequestline", "quantity", "requested_quantity"),
        migrations.RenameField("purchaserequestline", "reason", "note"),
        migrations.RenameModel("PurchaseOrderItem", "PurchaseOrderLine"),
        migrations.RenameField("purchaseorderline", "quantity", "ordered_quantity"),
        migrations.AddField("purchaseorder", "created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="purchase_orders_created", to=settings.AUTH_USER_MODEL, verbose_name="Siparişi Oluşturan")),
        migrations.AddField("purchaseorder", "delivery_address", models.TextField(blank=True, verbose_name="Teslimat Adresi")),
        migrations.AddField("purchaseorder", "payment_term_days", models.PositiveIntegerField(default=30, verbose_name="Ödeme Vadesi (Gün)")),
        migrations.AddField("purchaserequest", "source", models.CharField(choices=[("manual", "Manuel"), ("stock_alert", "Otomatik Stok Uyarısı")], default="manual", max_length=20, verbose_name="Talep Kaynağı")),
        migrations.AddField("purchaserequest", "approval_note", models.TextField(blank=True, verbose_name="Onay / Red Notu")),
        migrations.AddField("purchaserequest", "approved_at", models.DateTimeField(blank=True, null=True, verbose_name="Onay Tarihi")),
        migrations.AddField("purchaserequest", "approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="purchase_requests_approved", to=settings.AUTH_USER_MODEL, verbose_name="Onaylayan Kullanıcı")),
        migrations.AddField("supplier", "commercial_title", models.CharField(blank=True, max_length=250, verbose_name="Ticari Unvan")),
        migrations.AddField("supplier", "contact_title", models.CharField(blank=True, max_length=100, verbose_name="Yetkili Ünvanı")),
        migrations.AddField("supplier", "mobile_phone", models.CharField(blank=True, max_length=30, verbose_name="Cep Telefonu")),
        migrations.AddField("supplier", "website", models.URLField(blank=True, verbose_name="Web Sitesi")),
        migrations.AddField("supplier", "tax_office", models.CharField(blank=True, max_length=100, verbose_name="Vergi Dairesi")),
        migrations.AddField("supplier", "mersis_number", models.CharField(blank=True, max_length=30, verbose_name="MERSİS Numarası")),
        migrations.AddField("supplier", "city", models.CharField(blank=True, max_length=100, verbose_name="İl")),
        migrations.AddField("supplier", "district", models.CharField(blank=True, max_length=100, verbose_name="İlçe")),
        migrations.AddField("supplier", "country", models.CharField(default="Türkiye", max_length=100, verbose_name="Ülke")),
        migrations.AddField("supplier", "postal_code", models.CharField(blank=True, max_length=20, verbose_name="Posta Kodu")),
        migrations.AddField("supplier", "currency", models.CharField(default="TRY", max_length=3, verbose_name="Varsayılan Para Birimi")),
        migrations.AddField("supplier", "bank_name", models.CharField(blank=True, max_length=150, verbose_name="Banka Adı")),
        migrations.AddField("supplier", "iban", models.CharField(blank=True, max_length=34, verbose_name="IBAN")),
        migrations.AddField("supplier", "notes", models.TextField(blank=True, verbose_name="Notlar")),
        migrations.AddField("supplier", "payment_term_days", models.PositiveIntegerField(default=30, verbose_name="Ödeme Vadesi (Gün)")),
        migrations.AlterField("purchaseorder", "purchase_request", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="purchase_order", to="procurement.purchaserequest", verbose_name="Kaynak Satın Alma Talebi")),
        migrations.AlterField("purchaseorder", "order_date", models.DateField(verbose_name="Sipariş Tarihi")),
        migrations.AlterField("purchaseorder", "status", models.CharField(choices=[("draft", "Taslak"), ("sent", "Tedarikçiye Gönderildi"), ("partially_received", "Kısmi Teslim Alındı"), ("completed", "Tamamlandı"), ("cancelled", "İptal")], default="draft", max_length=30, verbose_name="Durum")),
        migrations.AlterField("purchaserequest", "requested_at", models.DateTimeField(auto_now_add=True, verbose_name="Talep Tarihi")),
        migrations.AlterField("purchaserequest", "requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="purchase_requests_created", to=settings.AUTH_USER_MODEL, verbose_name="Talebi Oluşturan")),
        migrations.AlterField("purchaserequest", "required_date", models.DateField(blank=True, null=True, verbose_name="İhtiyaç Tarihi")),
        migrations.AlterField("purchaserequest", "status", models.CharField(choices=[("draft", "Taslak"), ("pending_approval", "Onay Bekliyor"), ("approved", "Onaylandı"), ("rejected", "Reddedildi"), ("converted", "Siparişe Dönüştü"), ("cancelled", "İptal")], default="draft", max_length=30, verbose_name="Durum")),
        migrations.AlterField("supplier", "tax_number", models.CharField(blank=True, max_length=30, verbose_name="Vergi Numarası / TCKN")),
        migrations.AlterField("purchaserequestline", "note", models.CharField(blank=True, max_length=250, verbose_name="Kalem Notu")),
        migrations.AlterField("purchaserequestline", "product", models.ForeignKey(limit_choices_to={"product_type": "finished_good"}, on_delete=django.db.models.deletion.PROTECT, related_name="purchase_request_lines", to="inventory.product", verbose_name="Bitmiş Ürün")),
        migrations.AlterField("purchaserequestline", "purchase_request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="procurement.purchaserequest", verbose_name="Satın Alma Talebi")),
        migrations.AlterField("purchaseorderline", "product", models.ForeignKey(limit_choices_to={"product_type": "finished_good"}, on_delete=django.db.models.deletion.PROTECT, related_name="purchase_order_lines", to="inventory.product", verbose_name="Bitmiş Ürün")),
        migrations.AlterField("purchaseorderline", "purchase_order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="procurement.purchaseorder", verbose_name="Satın Alma Siparişi")),
        migrations.AddField("purchaseorderline", "note", models.CharField(blank=True, max_length=250, verbose_name="Kalem Notu")),
        migrations.AddConstraint("purchaserequestline", models.UniqueConstraint(fields=("purchase_request", "product"), name="unique_purchase_request_product")),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField("purchaseorder", "total_amount"),
                migrations.RemoveField("purchaseorderline", "tax_rate"),
                migrations.RemoveField("supplier", "delivery_lead_time_days"),
                migrations.RemoveField("supplier", "payment_terms"),
                migrations.DeleteModel("GoodsReceipt"),
                migrations.DeleteModel("GoodsReceiptItem"),
                migrations.DeleteModel("SupplierProduct"),
            ],
            database_operations=[],
        ),
        migrations.AlterModelOptions("purchaseorder", options={"ordering": ["-order_date", "-id"], "verbose_name": "Satın Alma Siparişi", "verbose_name_plural": "Satın Alma Siparişleri"}),
        migrations.AlterModelOptions("purchaserequestline", options={"ordering": ["id"], "verbose_name": "Satın Alma Talep Kalemi", "verbose_name_plural": "Satın Alma Talep Kalemleri"}),
        migrations.AlterModelOptions("purchaseorderline", options={"ordering": ["id"], "verbose_name": "Satın Alma Sipariş Kalemi", "verbose_name_plural": "Satın Alma Sipariş Kalemleri"}),
        migrations.AlterModelOptions("supplier", options={"ordering": ["code"], "verbose_name": "Tedarikçi", "verbose_name_plural": "Tedarikçiler"}),
    ]
