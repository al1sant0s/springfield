from django.db.utils import settings
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from pathlib import Path

import json
import uuid
# Create your views here.

def getDirectionByPackage(request, platform):

    directions_android = cache.get("directions_android")
    connect_list_index = cache.get("connect_list_index")

    if directions_android is None:

        response = Path("director/responses/getdirectionbypackage.json")
        with open(response, "r") as f:
            directions_android  = json.load(f)

        # Override platform.
        directions_android["clientId"] = directions_android["clientId"].replace("platform", platform)
        directions_android["mdmAppKey"] = directions_android["mdmAppKey"].replace("platform", platform)

        # Load settings and override urls.
        with open("config.json", "r") as f:
            config = json.load(f)
            protocol = config["protocol"]
            proxy = config["host"]
            port = config["port"]
            for i in range(len(directions_android["serverData"])):
                item = directions_android["serverData"][i]
                item.update({"value": f"{protocol}://{proxy}:{port}"})
                if item["key"] == "nexus.connect":
                    connect_list_index = i

            cache.set("directions_android", directions_android, timeout = config["cache_minutes"])
            cache.set("connect_list_index", connect_list_index, timeout = config["cache_minutes"])


    # Add an exclusive id for the connect app.
    connect_id = uuid.uuid4()
    directions_android["serverData"][connect_list_index]["value"] += f"/connect/{connect_id}"

    return JsonResponse(directions_android)
