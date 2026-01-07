from django.http import HttpResponse, JsonResponse
from pathlib import Path

import random, json, hashlib

# Create your views here.

def getDeviceID(request):
    response = {
        "deviceId": hashlib.sha256(json.dumps(request.GET, sort_keys=True).encode()).hexdigest(),
        "resultCode": 0,
        "serverApiVersion": "1.0.0"
    }

    return JsonResponse(response)


def getAnonUid(request):
    response = {
        "uid": request.GET["eadeviceid"],
        "resultCode": 0,
        "serverApiVersion": "1.0.0",
    }

    return JsonResponse(response)
