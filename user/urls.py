from django.urls import path

from . import views

app_name = "user"
urlpatterns = [
    path("api/<str:platform>/getAnonUid", views.getAnonUid, name="getAnonUid"),
    path("api/<str:platform>/getDeviceID", views.getDeviceID, name="getDeviceID"),
    path("api/<str:platform>/validateDeviceID", views.validateDeviceID, name="validateDeviceID")
]
