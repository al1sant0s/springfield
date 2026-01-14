from django.urls import path

from . import views

app_name = "avatar"
urlpatterns = [
    path("user//avatars", views.get_avatar, name="get_avatar"),
    path("user/<str:users_ids>/avatars", views.get_avatars, name="get_avatars"),
]
