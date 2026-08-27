from django.urls import path, include

from . import views

app_name = "ai"

urlpatterns = [
    path("ask/", views.ask, name="ask"),
]