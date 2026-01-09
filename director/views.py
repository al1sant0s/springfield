from django.db.utils import settings
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from pathlib import Path

import json
# Create your views here.

def getDirectionByPackage(request, platform):

    directions_android = cache.get("directions_android")

    if directions_android  is None:

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
            for item in directions_android["serverData"]:
                item = item.update({"value": f"{protocol}://{proxy}:{port}"})

            cache.set("directions_android", directions_android, timeout = config["cache_minutes"])

    return JsonResponse(directions_android)
