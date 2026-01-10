from django.urls import path

from . import views

app_name = "mh"
urlpatterns = [
    path("games/lobby/time", views.get_current_time, name="time"),
    path("gameplayconfig", views.gameplayconfig, name="gameplayconfig"),
    path("users", views.users, name="users"),
    path("userstats", views.userstats, name="userstats"),
    path("clienttelemetry/", views.clienttelemetry, name="clienttelemetry"),
    path("games/bg_gameserver_plugin/trackinglog/", views.trackinglog, name="trackinglog"),
    path("games/bg_gameserver_plugin/protoClientConfig/", views.protoClientConfig, name="protoClientConfig"),
    path("games/bg_gameserver_plugin/friendData", views.friendData, name="friendData"),
    path("games/bg_gameserver_plugin/friendData/origin", views.friendData, name="friendDataOrigin"),
    path("games/bg_gameserver_plugin/protoWholeLandToken/<int:mayhem_id>/", views.protoWholeLandToken, name="protoWholeLandToken"),
    path("games/bg_gameserver_plugin/deleteToken/<int:mayhem_id>/protoWholeLandToken/", views.deleteToken, name="deleteToken"),
    path("games/bg_gameserver_plugin/protoland/<int:mayhem_id>/", views.protoland, name="protoland"),
    path("games/bg_gameserver_plugin/protocurrency/<int:mayhem_id>/", views.protocurrency, name="protocurrency"),
    path("games/bg_gameserver_plugin/checkToken/<int:mayhem_id>/protoWholeLandToken/", views.checkToken, name="checkToken"),
    path("games/bg_gameserver_plugin/extraLandUpdate/<int:mayhem_id>/protoland/", views.extraLandUpdate, name="extraLandUpdate"),
    path("games/bg_gameserver_plugin/event/<int:mayhem_id>/protoland/", views.event_user, name="event_user"),
    path("games/bg_gameserver_plugin/event/fakefriend/protoland/", views.event_fakefriend, name="event_fakefriend"),
]
