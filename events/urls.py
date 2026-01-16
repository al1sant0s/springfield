from django.urls import path

from . import views

app_name = "events"
urlpatterns = [
    path("river.pin/<uuid:device_id>/pinEvents", views.pinEvents, name="pinEvents"),
    path("tracking/api/core/logEvent", views.logEvent, name="logEvent"),
]
