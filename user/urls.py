from django.urls import path

from . import views

app_name = "user"
urlpatterns = [
    path("api/android/getAnonUid", views.getAnonUid, name="getAnonUid"),
    path("api/android/getDeviceID", views.getDeviceID, name="getDeviceID"),
]
