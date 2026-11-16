import copy
import json
import uuid
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


def getDirectionByPackage(request, platform):
    directions_android = cache.get("directions_android")
    services = cache.get("services")

    if directions_android is None or services is None:
        response = Path("director/responses/getdirectionbypackage.json")
        with open(response, "r") as f:
            directions_android = json.load(f)

        # Load settings and override urls.
        services = {
            service["key"]: settings.SERVER_BASE_URL
            for service in directions_android["serverData"]
        }

        cache.set("directions_android", directions_android)
        cache.set("services", services)

    # Add an exclusive id for some apps.
    device_id = uuid.uuid4()

    update_services = [
        "nexus.connect",
        "synergy.tracking",
        "synergy.user",
        "river.pin",
    ]

    # Override platform.
    new_directions_android = copy.deepcopy(directions_android)
    new_directions_android["clientId"] = new_directions_android["clientId"].replace(
        "platform", platform
    )
    new_directions_android["mdmAppKey"] = new_directions_android["mdmAppKey"].replace(
        "platform", platform
    )

    for service in update_services:
        services[service] = f"{settings.SERVER_BASE_URL}/{service}/{device_id}"

    new_directions_android["serverData"] = [
        {"key": key, "value": value} for key, value in services.items()
    ]

    return JsonResponse(new_directions_android)
