from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("stock-levels/", views.stock_level_list, name="stock_level_list"),
    path("stock-movements/", views.stock_movement_list, name="stock_movement_list"),
    path("lot-tracking/", views.lot_tracking_list, name="lot_tracking_list"),
    path(
        "products/<int:product_pk>/movements/",
        views.product_movement_history,
        name="product_movement_history",
    ),
]
