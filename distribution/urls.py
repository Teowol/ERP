from django.urls import path

from . import views

app_name = "distribution"

urlpatterns = [
    path("", views.sales_order_list, name="sales_order_list"),
    path("create/", views.sales_order_create, name="sales_order_create"),
    path("<int:pk>/", views.sales_order_detail, name="sales_order_detail"),
    path("<int:pk>/edit/", views.sales_order_edit, name="sales_order_edit"),
    path("<int:pk>/confirm/", views.sales_order_confirm, name="sales_order_confirm"),
    path("<int:pk>/cancel/", views.sales_order_cancel, name="sales_order_cancel"),
    path("line/<int:line_pk>/produce/", views.create_production_order_from_line, name="create_production_order_from_line"),
    path("invoice/<int:invoice_pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),

    path("musteri/siparislerim/", views.customer_order_list, name="customer_order_list"),
    path("musteri/siparis/<int:pk>/", views.customer_order_detail, name="customer_order_detail"),
    path("musteri/satin-al/", views.customer_purchase, name="customer_purchase"),
    path("musteri/satin-al/<int:variant_pk>/", views.customer_purchase_detail, name="customer_purchase_detail"),
    path("musteri/varyant/<int:variant_pk>/siparis-ver/", views.customer_create_order, name="customer_create_order"),
]