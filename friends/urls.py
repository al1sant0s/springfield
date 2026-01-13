
from django.urls import path

from . import views

app_name = "friends"
urlpatterns = [
    path("2/users/<int:user_id>/invitations/outbound", views.outbound, name="outbound"),
    path("2/users/<int:user_id>/invitations/outbound/<int:pid_id>", views.outbound_sent, name="outbound_sent"),
    path("2/users/<int:user_id>/invitations/inbound", views.inbound, name="inbound"),
    path("2/users/<int:to_user_id>/invitations/inbound/<int:from_user_id>", views.inbound_accept, name="inbound_accept"),
    path("2/users/<int:user_id>/friends", views.get_friends, name="get_friends"),
]
