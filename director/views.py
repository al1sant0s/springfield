from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from pathlib import Path

import json
# Create your views here.

def json_view(request):
    json_data = cache.get('my_json_data')
    
    if json_data is None:
        # Read from file and cache it
        with open('path/to/your/file.json', 'r') as f:
            json_data = json.load(f)
        # Cache for a long time (e.g., 1 day or more)
        cache.set('my_json_data', json_data, timeout=60*60*24)
    
    return JsonResponse(json_data)

def get_directions_android(request):

    json_data = cache.get("directions_android")

    if json_data is None:

        response = Path("director/api/android/getdirectionbypackage.json")
        with open(response, "r") as f:
            json_data = json.load(f)


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
