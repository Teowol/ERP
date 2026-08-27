from django.urls import path

from . import views

app_name = "procurement"

urlpatterns = [
    path("", views.purchase_request_list, name="purchase_request_list"),
]
