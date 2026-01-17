from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from pathlib import Path
from connect.models import UserId, DeviceToken

import gzip
import json

# Create your views here.

@require_POST
@csrf_exempt
def pinEvents(request, device_id):


    # Try to decompress.
    try:
        decompressed_data = gzip.decompress(request.body)

    except gzip.BadGzipFile:
        decompressed_data = request.body

    json_data = json.loads(decompressed_data)
    pidm = json_data[0].get("contexts", [dict()])[0].get("pidm")

    if pidm is not None:

        if pidm.get("nucleus") is not None:
            token = get_object_or_404(DeviceToken, device_id=device_id)

            if not token.login_status:
                token.login_status = True
                token.save()


    return JsonResponse({"status": "ok"})


@require_POST
@csrf_exempt
def logEvent(request):

    response = {
        "status": "ok"
    }

    return JsonResponse(response)
