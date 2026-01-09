from django.urls import path

from . import views

app_name = "proxy"
urlpatterns = [
    path("identity/geoagerequirements", views.geoagerequirements, name="geoagerequirements"),
    path("identity/pids/me/personas/<int:persona_id>", views.me_persona , name="me_persona"),
    path("identity/pids//personas", views.me_personas , name="me_personas")
]

