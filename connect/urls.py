from django.urls import path

from . import views

import uuid

app_name = "connect"

# FORMAT: domain.com/app_name/app_name_id/endpoint/
# The format is defined in the views of the director app.
urlpatterns = [
    path("<uuid:connect_id>/connect/auth", views.auth, name="auth"),
    path("<uuid:connect_id>/connect/token", views.get_token, name="token"),
    path("<uuid:connect_id>/connect/tokeninfo", views.tokeninfo, name="tokeninfo"),
    path("<uuid:connect_id>/probe", views.probe, name="probe"),
]
