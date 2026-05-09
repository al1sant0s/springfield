from django.urls import path

from . import views

app_name = "director"
urlpatterns = [
    path("api/<str:platform>/getDirectionByPackage", views.getDirectionByPackage, name="getDirectionByPackage"),
    path("api/<str:platform>/getDirectionByBundle", views.getDirectionByPackage, name="getDirectionByBundle")
]
