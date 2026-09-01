from django.urls import path
from . import views

app_name = "production"

urlpatterns = [
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/action/<str:action>/", views.production_order_action, name="order_action"),
    path("costs/", views.cost_list, name="cost_list"),
    path("operations/", views.operation_list, name="operation_list"),
    path("operations/<int:pk>/action/<str:action>/", views.operation_action, name="operation_action"),
]