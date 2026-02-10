from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

import json
import gzip
import uuid

from connect.models import DeviceToken

# Create your views here.

def index(request):
    return HttpResponse("<h1>Hello, World!</h1>")

@require_POST
@csrf_exempt
def pinEvents(request):


    # Try to decompress.
    try:
        decompressed_data = gzip.decompress(request.body)

    except gzip.BadGzipFile:
        decompressed_data = request.body


    json_data = json.loads(decompressed_data)

    if "didm" in json_data[0]:

        device_id = uuid.UUID(json_data[0]["didm"].get("eadeviceid"))
        print(device_id)
        token = get_object_or_404(
            DeviceToken,
            Q(device_id=device_id) |
            Q(device_id_cache=device_id)
        )

        if "custom" in json_data[0]:

            token.manufacturer = json_data[0]["custom"].get("deviceBrand", "unknown")
            token.device_model = json_data[0]["custom"].get("deviceModel", "unknown")
            token.save(update_fields=["manufacturer", "device_model"])


    return JsonResponse({"status": "ok"})


@require_POST
@csrf_exempt
def logEvent(request, device_id):

    json_data = json.loads(request.body)
    advertising_id = json_data[0].get("advertiserID")

    if advertising_id is not None:
        try:
            token = DeviceToken.objects.get(advertising_id=uuid.uuid5(uuid.NAMESPACE_OID, advertising_id))

        except DeviceToken.DoesNotExist:
            pass

        else:
            if token.device_id != device_id:

                # Update device_id.
                token.device_id_cache = token.device_id
                token.device_id = device_id

                # Logout user if this is a reinstall.
                if json_data[0].get("persona") is None:
                    token.login_status = False

                token.save(update_fields=["device_id_cache", "device_id", "login_status"])

    response = {
        "status": "ok"
    }

    return JsonResponse(response)
