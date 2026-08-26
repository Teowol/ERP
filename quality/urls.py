from django.urls import path

from . import views

app_name = "quality"

urlpatterns = [
    path("", views.quality_check_list, name="quality_check_list"),
    path("create/<int:order_pk>/", views.quality_check_create, name="quality_check_create"),
    path("delete/<int:pk>/", views.quality_check_delete, name="quality_check_delete"),
]
