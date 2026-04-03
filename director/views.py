from django.http import JsonResponse
from django.core.cache import cache
from pathlib import Path

from springfield.settings import env

import json
import uuid


def getDirectionByPackage(request, platform):

    directions_android = cache.get("directions_android")
    services = cache.get("services")

    cache.set("directions_android", None)

    if directions_android is None:

        response = Path("director/responses/getdirectionbypackage.json")
        with open(response, "r") as f:
            directions_android  = json.load(f)

        # Override platform.
        directions_android["clientId"] = directions_android["clientId"].replace("platform", platform)
        directions_android["mdmAppKey"] = directions_android["mdmAppKey"].replace("platform", platform)

        # Load settings and override urls.
        protocol = env("PROTOCOL")
        domain = env("DOMAIN")
        port = env("PORT")
        timeout = env("CACHE_SECONDS", default=3600)
        services = {directions_android["serverData"][i]["key"]: i for i in range(len(directions_android["serverData"]))}

        for i in services.values():
            directions_android["serverData"][i]["value"] = f"{protocol}://{domain}:{port}"

        cache.set("directions_android", directions_android, timeout=timeout)
        cache.set("services", services, timeout=timeout)

    # Add an exclusive id for some apps.
    device_id = uuid.uuid4()

    update_services = [
        "nexus.connect",
        "synergy.tracking",
        "synergy.user",
        "river.pin",
    ]

    for service in update_services:
        directions_android["serverData"][services[service]]["value"] += f"/{service}/{device_id}"

    return JsonResponse(directions_android)
