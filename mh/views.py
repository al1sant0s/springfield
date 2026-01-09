from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

from protofiles import *
from pathlib import Path

import xml.etree.ElementTree as ET
import json
import time



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

        for entry in json_data:
            for keys, values in entry.items():
                setattr(clientconfig_response.items.add(), keys, values)

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

        for entry in json_data:
            for keys, values in entry.items():
                setattr(gameplayconfig_response.item.add(), keys, values)

        gameplayconfig_response = gameplayconfig_response.SerializeToString()

        with open("config.json", "r") as f:
            config = json.load(f)
            cache.set("gameplayconfig_response", gameplayconfig_response, timeout = config["cache_minutes"])


    return HttpResponse(gameplayconfig_response, content_type = "application/x-protobuf")




