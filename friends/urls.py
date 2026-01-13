
from django.urls import path

from . import views

app_name = "friends"
urlpatterns = [
    path("2/users/<int:user_id>/invitations/outbound", views.outbound, name="outbound"),
    path("2/users/<int:user_id>/invitations/outbound/<int:pid_id>", views.outbound_sent, name="outbound_sent"),
    path("2/users/<int:user_id>/invitations/inbound", views.inbound, name="inbound"),
]
