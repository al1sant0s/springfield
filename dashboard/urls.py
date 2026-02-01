from django.urls import path, reverse
from django.contrib.auth.views import LogoutView

from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login, name="login"),
    path("logout/", LogoutView.as_view(next_page="dashboard:login"), name="logout"),
    path("auth/", views.auth, name="auth"),
    path("register/", views.register, name="register"),
    path("forgot/password/", views.forgot_password, name="forgot_password"),
    path("reset/password/", views.reset_password, name="reset_password"),
]

