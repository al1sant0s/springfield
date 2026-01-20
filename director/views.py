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
    services = cache.get("services")

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
            host = config["host"]
            port = config["port"]
            services = {directions_android["serverData"][i]["key"]: i for i in range(len(directions_android["serverData"]))}

            for i in services.values():
                directions_android["serverData"][i]["value"] = f"{protocol}://{host}:{port}"

            cache.set("directions_android", directions_android, timeout = config["cache_minutes"])
            cache.set("services", services, timeout = config["cache_minutes"])


    # Add an exclusive id for some apps.
    device_id = uuid.uuid4()

    update_services = [
        "nexus.connect",
        "synergy.tracking",
    ]

    for service in update_services:
        directions_android["serverData"][services[service]]["value"] += f"/{service}/{device_id}"

    return JsonResponse(directions_android)
