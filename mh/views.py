from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.db.models import F
from django.views.decorators.csrf import csrf_exempt

from connect.models import DeviceToken, UserId
from pathlib import Path
from protofiles import *

import xml.etree.ElementTree as ET
import json
import gzip
import time
import uuid
import os


def get_towns_dir():

    towns_dir = cache.get("towns_dir")
    if towns_dir is None:
        with open("config.json", "r") as f:
            config = json.load(f)
            towns_dir = Path(config["towns_dir"])
            cache.set("towns_dir", towns_dir, timeout = config["cache_minutes"])

        if not towns_dir.exists():
            towns_dir.mkdir()

    return towns_dir


def save_proto(target, proto_data):

    proto_data = proto_data.SerializeToString()

    with open(target, "wb") as f:
        f.write(proto_data)


def load_proto(target, proto_object):

    if not target.exists():
        return proto_object

    else:
        with open(target, "rb") as f:
            proto_object.ParseFromString(f.read())

        return proto_object


def load_town(mayhem_id):

    user = UserId.objects.get(mayhem_id=mayhem_id)

    town_file = Path(get_towns_dir(), f"{mayhem_id}/{mayhem_id}.pb")
    land_data = LandData_pb2.LandMessage()

    # Create a new fresh town if one does not exist already.
    if not town_file.exists():
        land_data.friendData.dataVersion = 72
        land_data.friendData.hasLemonTree = False
        land_data.friendData.language = 0
        land_data.friendData.level = 0
        land_data.friendData.name = user.username
        land_data.friendData.rating = 0
        land_data.friendData.boardwalkTileCount = 0
        town_file.parent.mkdir(parents=True)
        save_proto(town_file, land_data)

    else:

        # Credits: Tjac python server.
        with open(town_file, "rb") as f:

            try:
                land_data.ParseFromString(f.read())

            except:

                try:
                    f.seek(0x0c)      # see if this might be a teamtsto.org backup
                    land_data.ParseFromString(f.read())

                # If everything fails just make a new town.
                except:
                    land_data.friendData.dataVersion = 72
                    land_data.friendData.hasLemonTree = False
                    land_data.friendData.language = 0
                    land_data.friendData.level = 0
                    land_data.friendData.name = user.username
                    land_data.friendData.rating = 0
                    land_data.friendData.boardwalkTileCount = 0

            # Override Mayhem id.
            if land_data.HasField("id") and land_data.id != str(mayhem_id):
                land_data.id = str(mayhem_id)
                save_proto(town_file, land_data)


    return land_data


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

    response = {
        "user": {
            "userId": "123456789",
            "telemetryId": "123456789"
        },
        "token": {
            "sessionKey": "123456789"
        }
    }

    application_user_id = request.GET.get("applicationUserId", "")
    if application_user_id != "":

        # Get a proper response.
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

    return HttpResponse(user_response.SerializeToString(), content_type = "application/x-protobuf")


@csrf_exempt
def userstats(request):
    telemetry_id = request.GET.get("synergy_id")
    if telemetry_id is not None:
        # Store currentClientSessionId in user's device token.
        user = get_object_or_404(UserId, telemetry_id=int(telemetry_id))
        token = user.devicetoken_set.first()
        token.current_client_session_id = uuid.UUID(request.headers.get("currentClientSessionId"))
        token.save()

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

        with open("config.json", "r") as f:

            config = json.load(f)
            protocol = config["protocol"]
            host = config["host"]
            port = config["port"]

            # Avatar change url.
            for item in json_data:
                if item["clientConfigId"] == 52:
                    item["value"] = f"{protocol}://{host}:{port}"

            clientconfig_response = ClientConfigData_pb2.ClientConfigResponse()

            for obj in json_data:
                entry = clientconfig_response.items.add()
                for key, value in obj.items():
                    setattr(entry, key, value)

            clientconfig_response = clientconfig_response.SerializeToString()
            cache.set("clientconfig", clientconfig_response, timeout = config["cache_minutes"])


    return HttpResponse(clientconfig_response, content_type = "application/x-protobuf")


@csrf_exempt
def friendData(request):


    friend_data_pairs = list()
    mayhem_ids = list()

    debug_mayhem_id = request.GET.get("debug_mayhem_id")
    current_client_session_id = request.headers.get("currentClientSessionId")

    # Find user friends.
    if debug_mayhem_id is not None:
        mayhem_ids.append(int(debug_mayhem_id))

    elif current_client_session_id is None:
        return HttpResponseBadRequest("Missing header currentClientSessionId.")

    else:
        user = get_object_or_404(DeviceToken, current_client_session_id=uuid.UUID(current_client_session_id)).user

        for friend in user.friends.exclude(pk=user.pk):
            mayhem_ids.append(friend.mayhem_id.int)


    for mayhem_id in mayhem_ids:

        user = get_object_or_404(UserId, mayhem_id=uuid.UUID(int=mayhem_id))

        friend_data_pair = GetFriendData_pb2.GetFriendDataResponse.FriendDataPair(friendId=str(user.mayhem_id.int))
        friend_data_pair.friendData.name = user.username
        friend_data_pair.authService = 0
        friend_data_pair.externalId = str(user.user_id)

        # Attempt to find more town info.
        land_data = load_town(mayhem_id)
        friend_data_pair.friendData.dataVersion = land_data.friendData.dataVersion
        friend_data_pair.friendData.hasLemonTree = land_data.friendData.hasLemonTree
        friend_data_pair.friendData.language = land_data.friendData.language
        friend_data_pair.friendData.level = land_data.friendData.level
        friend_data_pair.friendData.rating = land_data.friendData.rating
        friend_data_pair.friendData.spendable.extend(list(land_data.friendData.spendable))
        friend_data_pair.friendData.landVersion  = land_data.friendData.landVersion 
        friend_data_pair.friendData.sublandInfos.extend(list(land_data.friendData.sublandInfos))
        friend_data_pair.friendData.boardwalkTileCount = land_data.friendData.boardwalkTileCount
        friend_data_pair.friendData.lastPlayedTime = land_data.friendData.lastPlayedTime
        friend_data_pair.friendData.sharedVariableSet.variable.extend(list(land_data.friendData.sharedVariableSet.variable))


        friend_data_pairs.append(friend_data_pair)



    friend_data_response = GetFriendData_pb2.GetFriendDataResponse()
    friend_data_response.friendData.extend(friend_data_pairs)

    return HttpResponse(friend_data_response.SerializeToString(), content_type = "application/x-protobuf")


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

    return HttpResponse(proto_whole_land_token_response.SerializeToString(), content_type = "application/x-protobuf")


@csrf_exempt
def deleteToken(request, mayhem_id):

    delete_token_response = WholeLandTokenData_pb2.DeleteTokenResponse()
    delete_token_response.result = True
    return HttpResponse(delete_token_response.SerializeToString(), content_type = "application/x-protobuf")


@csrf_exempt
def protoland(request, mayhem_id):

    user = get_object_or_404(UserId, mayhem_id = uuid.UUID(int=mayhem_id))
    protoland_response = LandData_pb2.LandMessage()

    #town_file = Path(towns_dir, "mytown.pb") # For testing purposes.


    # Load town.
    if request.method == "GET":

        protoland_response = load_town(mayhem_id)

        return HttpResponse(protoland_response.SerializeToString(), content_type = "application/x-protobuf")

    elif request.method == "POST":

        # Try to decompress.
        try:
            decompressed_data = gzip.decompress(request.body)

        except gzip.BadGzipFile:
            decompressed_data = request.body

        finally:

            # Update town.
            protoland_response.ParseFromString(decompressed_data) # type: ignore
            save_proto(Path(get_towns_dir(), f"{mayhem_id}/{mayhem_id}.pb"), protoland_response)

            # Remove events file if it exists.
            event_file = Path(get_towns_dir(), f"{mayhem_id}/{mayhem_id}.events")
            if event_file.exists():
                os.remove(event_file)

            root = ET.Element("WholeLandUpdateResponse")
            return HttpResponse(ET.tostring(root, "utf8", "xml"), content_type="application/xml")

    else:
        return HttpResponseBadRequest(f"Method '{request.method}' not supported!")



def protocurrency(request, mayhem_id):

    user = get_object_or_404(UserId, mayhem_id = uuid.UUID(int=mayhem_id))

    # Initial currency setup.
    protocurrency_response = PurchaseData_pb2.CurrencyData()
    protocurrency_response.id = str(mayhem_id)
    protocurrency_response.vcTotalPurchased = 0
    protocurrency_response.vcTotalAwarded = 0
    protocurrency_response.vcBalance = user.donuts_balance                    # number of donuts
    protocurrency_response.createdAt = int(round(time.time() * 1000))
    protocurrency_response.updatedAt = int(round(time.time() * 1000))
    return HttpResponse(protocurrency_response.SerializeToString(), content_type = "application/x-protobuf")


def checkToken(request, mayhem_id):

    user = get_object_or_404(UserId, mayhem_id = uuid.UUID(int=mayhem_id))

    checktoken_response = AuthData_pb2.TokenData()
    checktoken_response.sessionKey = user.session_key
    checktoken_response.expirationDate = 0
    return HttpResponse(checktoken_response.SerializeToString(), content_type = "application/x-protobuf")


@csrf_exempt
def extraLandUpdate(request, mayhem_id):

    user = get_object_or_404(UserId, mayhem_id = uuid.UUID(int=mayhem_id))

    # Update donuts balance.
    if request.method == "POST":

        # Try to decompress.
        try:
            decompressed_data = gzip.decompress(request.body)

        except gzip.BadGzipFile:
            decompressed_data = request.body

        finally:

            # Get list of events to update donuts.
            # Each event is a list with an amount to increase/decrease donuts balance.
            extraland_update_request = LandData_pb2.ExtraLandMessage()
            extraland_update_request.ParseFromString(decompressed_data) # type: ignore

            # There's also other stuff here like "reason" but we don't care about that.
            # Only update the donuts balance.
            processed_currency_delta = list()
            donuts_amount = 0
            for currency_delta in extraland_update_request.currencyDelta:
                donuts_amount += int(currency_delta.amount)
                processed_currency_delta.append(
                    LandData_pb2.ExtraLandMessage.CurrencyDelta(
                        id=currency_delta.id,
                        reason=currency_delta.reason,
                        amount=currency_delta.amount
                    )
                )

            # Update donuts balance in database.
            user.donuts_balance = F("donuts_balance") + donuts_amount
            user.save()

            # Note: you need to use extend() method if you define the response first and edit a repeated field later.
            # extraland_update_response = LandData_pb2.ExtraLandResponse()
            # extraland_update_response.processedCurrencyDelta.extend(processed_currency_delta)
            extraland_update_response = LandData_pb2.ExtraLandResponse(processedCurrencyDelta = processed_currency_delta)
            return HttpResponse(extraland_update_response.SerializeToString(), content_type = "application/x-protobuf")


    else:
        return HttpResponseBadRequest(f"Method '{request.method}' not supported!")


@csrf_exempt
def event_user(request, mayhem_id):

    if request.method == "POST":

        event_request = LandData_pb2.EventMessage()
        event_request.ParseFromString(request.body)
        event_request.id = str(uuid.uuid4())
        event_request.fromPlayerId = str(mayhem_id)
        event_file = Path(get_towns_dir(), f"{event_request.toPlayerId}/{event_request.toPlayerId}.events")
        event_data = load_proto(event_file, LandData_pb2.EventsMessage())
        event_data.event.extend([event_request])
        save_proto(event_file, event_data)

        root = ET.Element("Land")
        return HttpResponse(ET.tostring(root, "utf8", "xml"), content_type="application/xml")

    elif request.method == "GET":

        event_response = LandData_pb2.EventsMessage()
        event_file = Path(get_towns_dir(), f"{mayhem_id}/{mayhem_id}.events")

        if event_file.exists():
            event_response = load_proto(event_file, event_response)

        return HttpResponse(event_response.SerializeToString(), content_type = "application/x-protobuf")

    else:
        return HttpResponseBadRequest(f"The {request.method} is not supported.")


def event_fakefriend(request):
    fakefriend_response = LandData_pb2.LandMessage.FakeFriendData()
    return HttpResponse(fakefriend_response.SerializeToString(), content_type = "application/x-protobuf")
