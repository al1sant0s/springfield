from django.http import HttpResponse, JsonResponse

import json
import hashlib

# Create your views here.

def getDeviceID(request, platform):

    response = {
        "deviceId": hashlib.sha256(json.dumps(request.GET, sort_keys=True).encode()).hexdigest(),
        "resultCode": 0,
        "serverApiVersion": "1.0.0"
    }

    return JsonResponse(response)


def getAnonUid(request, platform):

    response = {
        "uid": request.GET["eadeviceid"],
        "resultCode": 0,
        "serverApiVersion": "1.0.0",
    }

    return JsonResponse(response)


def validateDeviceID(request, platform):

    response = {
        "deviceId": request.GET.get("eadeviceid", "NO-EADEVICEID-PROVIDED"),
        "resultCode": 0,
        "serverApiVersion": "1.0.0"
    }

    return JsonResponse(response)
