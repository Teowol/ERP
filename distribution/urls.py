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
    path("invoice/<int:invoice_pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
]
