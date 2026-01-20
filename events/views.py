from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

import json
import uuid

from connect.models import DeviceToken

# Create your views here.

@require_POST
@csrf_exempt
def pinEvents(request):
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

                token.save()

    response = {
        "status": "ok"
    }

    return JsonResponse(response)
