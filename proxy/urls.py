from django.urls import path

from . import views

app_name = "proxy"
urlpatterns = [
    path("<uuid:device_id>/proxy/identity/geoagerequirements", views.geoagerequirements, name="geoagerequirements"),
    path("<uuid:device_id>/proxy/identity/pids/me/personas/<int:persona_id>", views.me_personas , name="me_personas"),
    path("<uuid:device_id>/proxy/identity/pids//personas", views.personas, name="personas"),
    path("<uuid:device_id>/proxy/identity/pids/<int:user_id>/personas", views.user_id_personas , name="user_id_personas"),
    path("<uuid:device_id>/proxy/identity/progreg/code", views.progreg_code, name="progreg_code"),
    path("<uuid:device_id>/proxy/identity/links", views.links, name="links"),
]

