from django.urls import path

from . import views

app_name = "user"
urlpatterns = [
    path("<uuid:device_id>/user/api/<str:platform>/getAnonUid", views.getAnonUid, name="getAnonUid"),
    path("<uuid:device_id>/user/api/<str:platform>/getDeviceID", views.getDeviceID, name="getDeviceID"),
    path("<uuid:device_id>/user/api/<str:platform>/validateDeviceID", views.validateDeviceID, name="validateDeviceID")
]
