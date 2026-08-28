from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from core.views import customer_home, home, portal, register

urlpatterns = [
    path("", home, name="home"),
    path("portal/", portal, name="portal"),
    path("musteri/", customer_home, name="customer_home"),
    path("admin/", admin.site.urls),
    path("ai/", include("ai.urls")),
    path("giris/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("uye-ol/", register, name="register"),
    path("cikis/", auth_views.LogoutView.as_view(), name="logout"),
    path("catalog/", include("catalog.urls")),
    path("procurement/", include("procurement.urls")),
    path("inventory/", include("inventory.urls")),
    path("production/", include("production.urls")),
    path("quality/", include("quality.urls")),
    path("distribution/", include("distribution.urls")),
]
