from django.urls import path, reverse
from django.contrib.auth.views import LogoutView

from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.index, name="index"),
    path("profile/", views.profile, name="profile"),
    path("friends/", views.friends, name="friends"),
    path("friends/send/request/<int:to_user_id>", views.friends_send_request, name="friends_send_request"),
    path("friends/cancel/request/<int:to_user_id>", views.friends_cancel_request, name="friends_cancel_request"),
    path("friends/accept/request/<int:from_user_id>", views.friends_accept_request, name="friends_accept_request"),
    path("friends/reject/request/<int:from_user_id>", views.friends_reject_request, name="friends_reject_request"),
    path("friends/remove/<int:to_user_id>", views.friends_remove, name="friends_remove"),
    path("devices/", views.devices, name="devices"),
    path("devices/remove/<uuid:advertising_id>/", views.remove_device, name="remove_device"),
    path("login/", views.login, name="login"),
    path("logout/", LogoutView.as_view(next_page="dashboard:login"), name="logout"),
    path("auth/", views.auth, name="auth"),
    path("register/", views.register, name="register"),
    path("forgot/password/", views.forgot_password, name="forgot_password"),
    path("reset/password/", views.reset_password, name="reset_password"),
]

