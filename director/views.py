from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from pathlib import Path

import json
# Create your views here.

def getDirectionByPackage(request, platform):

    json_data = cache.get("directions_android")

    if json_data is None:

        response = Path("director/api/getdirectionbypackage.json")
        with open(response, "r") as f:
            json_data = json.load(f)

        # Override platform.
        json_data["clientId"] = json_data["clientId"].replace("platform", platform)
        json_data["mdmAppKey"] = json_data["mdmAppKey"].replace("platform", platform)

        # Load settings and override urls.
        with open("config.json", "r") as f:
            settings = json.load(f)
            protocol = settings["protocol"]
            proxy = settings["host"]
            port = settings["port"]
            for item in json_data["serverData"]:
                item = item.update({"value": f"{protocol}://{proxy}:{port}"})

        cache.set("directions_android", json_data, timeout = 3600)

    return JsonResponse(json_data)
