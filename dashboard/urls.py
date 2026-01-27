from django.urls import path, reverse
from django.contrib.auth.views import LoginView, LogoutView

from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.index, name="index"),
    path("login/", LoginView.as_view(template_name="dashboard/login.html", next_page="dashboard:index"), name="login"),
    path("logout/", LogoutView.as_view(next_page="dashboard:login"), name="logout"),
]

