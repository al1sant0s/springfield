
from django.urls import path

from . import views

app_name = "friends"
urlpatterns = [
    path("<uuid:device_id>/friends/2/users/<int:user_id>/invitations/outbound", views.outbound, name="outbound"),
    path("<uuid:device_id>/friends/2/users/<int:from_user_id>/invitations/outbound/<int:to_user_id>", views.outbound_sent, name="outbound_sent"),
    path("<uuid:device_id>/friends/2/users/<int:user_id>/invitations/inbound", views.inbound, name="inbound"),
    path("<uuid:device_id>/friends/2/users/<int:to_user_id>/invitations/inbound/<int:from_user_id>", views.inbound_accept, name="inbound_accept"),
    path("<uuid:device_id>/friends/2/users/<int:user_id>/friends", views.get_friends, name="get_friends"),
    path("<uuid:device_id>/friends/2/users/<int:from_user_id>/friends/<int:to_user_id>", views.cancel_friendship, name="cancel_friendship"),
]
