from django.urls import path
from . import views

app_name = "production"

urlpatterns = [
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/action/<str:action>/", views.production_order_action, name="order_action"),
]