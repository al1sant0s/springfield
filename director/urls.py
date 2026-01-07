from django.urls import path

from . import views

app_name = "director"
urlpatterns = [
    path("api/android/getDirectionByPackage", views.get_directions_android, name="getDirectionByPackage"),
]
