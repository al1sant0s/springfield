from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

from connect.models import UserId
from pathlib import Path
from protofiles import *

import xml.etree.ElementTree as ET
import json
import time
import secrets
import uuid



def get_current_time(request):
    root = ET.Element("Time")
    ET.SubElement(root, "epochMilliseconds").text = str(int(time.time() * 1000))
    return HttpResponse(ET.tostring(root, "utf8", "xml"), content_type="application/xml")


@csrf_exempt
def trackinglog(request):
    root = ET.Element("Resources")
    ET.SubElement(root, "URI").text = "OK"
    return HttpResponse(ET.tostring(root, "utf8", "xml"), content_type="application/xml")



def protoClientConfig(request):

    clientconfig_response = cache.get("clientconfig")

    if clientconfig_response is None:

        with open(Path("mh/responses/protoClientConfig.json"), "r") as f:
            json_data = json.load(f)

        clientconfig_response = ClientConfigData_pb2.ClientConfigResponse()

        for obj in json_data:
            entry = clientconfig_response.items.add()
            for key, value in obj.items():
                setattr(entry, key, value)

        clientconfig_response = clientconfig_response.SerializeToString()

        with open("config.json", "r") as f:
            config = json.load(f)
            cache.set("clientconfig", clientconfig_response, timeout = config["cache_minutes"])


    return HttpResponse(clientconfig_response, content_type = "application/x-protobuf")


def gameplayconfig(request):

    gameplayconfig_response = cache.get("gameplayconfig")

    if gameplayconfig_response is None:

        with open(Path("mh/responses/gameplayconfig.json"), "r") as f:
            json_data = json.load(f)

        gameplayconfig_response = GameplayConfigData_pb2.GameplayConfigResponse()

        for obj in json_data:
            entry = gameplayconfig_response.item.add()
            for key, value in obj.items():
                setattr(entry, key, value)

        gameplayconfig_response = gameplayconfig_response.SerializeToString()

        with open("config.json", "r") as f:
            config = json.load(f)
            cache.set("gameplayconfig_response", gameplayconfig_response, timeout = config["cache_minutes"])


    return HttpResponse(gameplayconfig_response, content_type = "application/x-protobuf")


@csrf_exempt
def users(request):

    application_user_id = request.GET.get("applicationUserId")

    if application_user_id is None:
        return HttpResponseBadRequest("Missing required attribute: applicationUserId")

    user = get_object_or_404(UserId, user_id = application_user_id)

    response = {
        "user": {
            "userId": str(user.mayhem_id.int),
            "telemetryId": str(user.telemetry_id)
        },
        "token": {
            "sessionKey": secrets.token_urlsafe(32)
        }
    }

    user_response = AuthData_pb2.UsersResponseMessage()
    for key, value in response.items():
        for subkey, subvalue in value.items():
            setattr(getattr(user_response, key), subkey, subvalue)

    user_response = user_response.SerializeToString()

    return HttpResponse(user_response, content_type = "application/x-protobuf")


@csrf_exempt
def friendData(request):

    friend_data_response = GetFriendData_pb2.GetFriendDataResponse()

    # Process friends.

    friend_data_response = friend_data_response.SerializeToString()

    return HttpResponse(friend_data_response, content_type = "application/x-protobuf")


@csrf_exempt
def protoWholeLandToken(request, mayhem_id):

    # Generate land token and save land token to user.

    user = get_object_or_404(UserId, mayhem_id = uuid.UUID(int=mayhem_id))

    response = {
        "token": str(user.land_token),
        "conflict": False,
    }

    proto_whole_land_token_response = WholeLandTokenData_pb2.WholeLandTokenResponse()
    for key, value in response.items():
        setattr(proto_whole_land_token_response, key, value)


    proto_whole_land_token_response = proto_whole_land_token_response.SerializeToString()

    return HttpResponse(proto_whole_land_token_response, content_type = "application/x-protobuf")
