from django.urls import path

from . import views

app_name = "connect"

# FORMAT: domain.com/service/device_id/endpoint/
# The format is defined in the views of the director app.
urlpatterns = [
    path("<uuid:device_id>/connect/auth", views.auth, name="auth"),
    path("<uuid:device_id>/connect/token", views.get_token, name="token"),
    path("<uuid:device_id>/connect/tokeninfo", views.tokeninfo, name="tokeninfo"),
    path("<uuid:device_id>/probe", views.probe, name="probe"),
]
