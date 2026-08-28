from django.urls import path

from . import views

app_name = "ai"

urlpatterns = [
    path("chat/", views.chat_page, name="chat_page"),
    path("ask/", views.ask, name="ask"),
]