from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
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


#######################################
# Common views.
#######################################

def get_current_time(request):
    root = ET.Element("Time")
    ET.SubElement(root, "epochMilliseconds").text = str(int(time.time() * 1000))
    return HttpResponse(ET.tostring(root, "utf8", "xml"), content_type="application/xml")


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
            "sessionKey": user.session_key
        }
    }

    user_response = AuthData_pb2.UsersResponseMessage()
    for key, value in response.items():
        for subkey, subvalue in value.items():
            setattr(getattr(user_response, key), subkey, subvalue)

    user_response = user_response.SerializeToString()

    return HttpResponse(user_response, content_type = "application/x-protobuf")


@csrf_exempt
def userstats(request):
    return HttpResponse(status=409)


@csrf_exempt
def clienttelemetry(request):
    return HttpResponse(ClientTelemetry_pb2.ClientTelemetryMessage().SerializeToString(), content_type = "application/x-protobuf")


#######################################
# Views related to bg_gameserver_plugin.
#######################################

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


@csrf_exempt
def deleteToken(request, mayhem_id):

    delete_token_response = WholeLandTokenData_pb2.DeleteTokenResponse()
    delete_token_response.result = True
    delete_token_response = delete_token_response.SerializeToString()
    return HttpResponse(delete_token_response, content_type = "application/x-protobuf")


@csrf_exempt
def protoland(request, mayhem_id):

    user = get_object_or_404(UserId, mayhem_id = uuid.UUID(int=mayhem_id))

    towns_dir = cache.get("towns_dir")
    if towns_dir is None:
        with open("config.json", "r") as f:
            config = json_load(f)
            towns_dir = Path(config["towns_dir"])
            cache.set("towns_dir", towns_dir, timeout = config["cache_minutes"])


        if not towns_dir.exists():
            towns_dir.mkdir()


    protoland_response = LandData_pb2.LandMessage()
    town_file = Path(towns_dir, f"{mayhem_id}.pb")

    # Create a new fresh town if one does not exist.
    if not town_file.exists():
        protoland_response.friendData.dataVersion = 72
        protoland_response.friendData.hasLemonTree = False
        protoland_response.friendData.language = 0
        protoland_response.friendData.level = 0
        protoland_response.friendData.name = user.username
        protoland_response.friendData.rating = 0
        protoland_response.friendData.boardwalkTileCount = 0
        protoland_response = protoland_response.SerializeToString()

    # Load town.
    if request.method == "GET":

        # Credits: Tjac python server.
        with open(town_file, "rb") as f:

            try:
                protoland_response.ParseFromString(f.read())

            except:
                try:
                    f.seek(0x0c)      # see if this might be a teamtsto.org backup
                    protoland_response.ParseFromString(f.read())

                # If everything fails just make a new town.
                except:
                    protoland_response = LandData_pb2.LandMessage()
                    protoland_response.friendData.dataVersion = 72
                    protoland_response.friendData.hasLemonTree = False
                    protoland_response.friendData.language = 0
                    protoland_response.friendData.level = 0
                    protoland_response.friendData.name = user.username
                    protoland_response.friendData.rating = 0
                    protoland_response.friendData.boardwalkTileCount = 0
                    protoland_response = protoland_response.SerializeToString()

            # Override mayhem id.
            else:
                protoland_response.id = mayhem_id

    elif request.method == "POST":
        protoland_response.ParseFromString(request.body)

    else:
        return HttpResponseBadRequest(f"Method '{request.method}' not supported!")

    # Save town.
    with open(town_file, "wb") as f:
        f.write(protoland_response)

    return HttpResponse(protoland_response, content_type = "application/x-protobuf")

def protocurrency(request, mayhem_id):

    # Initial currency setup.
    protocurrency_response = PurchaseData_pb2.CurrencyData()
    protocurrency_response.id = str(mayhem_id)
    protocurrency_response.vcTotalPurchased = 0
    protocurrency_response.vcTotalAwarded = 0
    protocurrency_response.vcBalance = 1234567                    # number of donuts
    protocurrency_response.createdAt = int(round(time.time() * 1000))
    protocurrency_response.updatedAt = int(round(time.time() * 1000))
    protocurrency_response = protocurrency_response.SerializeToString()
    return HttpResponse(protocurrency_response, content_type = "application/x-protobuf")


def checkToken(request, mayhem_id):

    user = get_object_or_404(UserId, mayhem_id = uuid.UUID(int=mayhem_id))

    checktoken_response = AuthData_pb2.TokenData()
    checktoken_response.sessionKey = user.session_key
    checktoken_response.expirationDate = 0
    checktoken_response = checktoken_response.SerializeToString()
    return HttpResponse(checktoken_response, content_type = "application/x-protobuf")


@csrf_exempt
def extraLandUpdate(request, mayhem_id):

    user = get_object_or_404(UserId, mayhem_id = uuid.UUID(int=mayhem_id))

    extraland_update_response = LandData_pb2.ExtraLandResponse()
    extraland_update_response = extraland_update_response.SerializeToString()
    return HttpResponse(extraland_update_response, content_type = "application/x-protobuf")


def event_user(request, mayhem_id):

    event_response = LandData_pb2.EventsMessage()
    event_response = event_response.SerializeToString()
    return HttpResponse(event_response, content_type = "application/x-protobuf")


def event_fakefriend(request):
    return JsonResponse({"status": "ok"})
