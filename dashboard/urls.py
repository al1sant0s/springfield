from django.urls import path, reverse
from django.contrib.auth.views import LogoutView

from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.check_login, name="login"),
    path("logout/", LogoutView.as_view(next_page="dashboard:login"), name="logout"),
]

