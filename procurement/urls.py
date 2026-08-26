from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="procurement_index"),
]
