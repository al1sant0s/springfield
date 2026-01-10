from django.urls import path

from . import views

app_name = "proxy"
urlpatterns = [
    path("identity/geoagerequirements", views.geoagerequirements, name="geoagerequirements"),
    path("identity/pids/me/personas/<int:persona_id>", views.me_personas , name="me_personas"),
    path("identity/pids//personas", views.personas, name="personas"),
    path("identity/pids/<int:user_id>/personas", views.user_id_personas , name="user_id_personas"),
    path("identity/progreg/code", views.progreg_code , name="progreg_code")
]

