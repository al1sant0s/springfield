from django.urls import path

from . import views

app_name = "events"
urlpatterns = [
    path("pinEvents", views.pinEvents, name="pinEvents"),
    path("probe", views.probe, name="probe"),
    path("tracking/api/core/logEvent", views.logEvent, name="logEvent")
]
