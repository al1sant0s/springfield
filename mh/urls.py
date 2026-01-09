from django.urls import path

from . import views

app_name = "mh"
urlpatterns = [
    path("games/lobby/time", views.get_current_time, name="time"),
    path("games/bg_gameserver_plugin/trackinglog/", views.trackinglog, name="trackinglog"),
    path("games/bg_gameserver_plugin/protoClientConfig/", views.protoClientConfig, name="protoClientConfig"),
    path("gameplayconfig", views.gameplayconfig, name="gameplayconfig"),
#    path("", views.IndexView.as_view(), name="index"),
#    path("<int:pk>/", views.DetailView.as_view(), name="detail"),
#    path("<int:pk>/results/", views.ResultsView.as_view(), name="results"),
#    path("<int:question_id>/vote/", views.vote, name="vote"),
]
