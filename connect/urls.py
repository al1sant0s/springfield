from django.urls import path

from . import views

app_name = "connect"
urlpatterns = [
    path("auth", views.auth, name="auth"),
    path("token", views.get_token, name="token"),
    path("tokeninfo", views.tokeninfo, name="tokeninfo")
]
