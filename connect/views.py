from os import access
from django.http import Http404, HttpResponse, JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import UserId, DeviceToken
from pathlib import Path

import math
import json
import jwt
import base64
import hashlib
import uuid
import time
import secrets


# Create your views here.

def auth(request):

    # Look up for advertisingId in database.
    jsondata = request.GET.get("sig").split(".")[0]
    jsondata += "=" * (math.ceil(len(jsondata) / 64) * 64 - len(jsondata))
    jsondata = json.loads(base64.b64decode(jsondata))
    advertising_id = uuid.uuid5(uuid.NAMESPACE_OID, jsondata["advertisingId"])

    # Grab existing DeviceToken. If it does not exist, make one.
    token = DeviceToken.objects.filter(advertising_id=advertising_id)

    if token.exists() is True:
        token = token.latest("id")

    else:
        # Each new token creates a new user.
        token = DeviceToken(advertising_id = advertising_id)

        try:
            last_user = UserId.objects.latest("id")
        except UserId.DoesNotExist:
            token.user = UserId(persona_id = 1001000000001)
        else:
            token.user = UserId(persona_id = last_user.persona_id + 1)

        token.user.user_id = token.user.persona_id + 20000000000
        token.user.pid_id = token.user.user_id + 200000
        token.user.telemetry_id = token.user.pid_id + 20000000000
        token.user.mayhem_id = uuid.uuid4().int
        token.user.username = f"anon{str(token.user.persona_id)[-5:]}"
        token.user.email = f"user_{str(token.user.mayhem_id)}@tsto.app"
        token.user.date_created = timezone.now()


    token.user.last_authenticated = timezone.now()
    token.user.save()

    # Generate new code and new access token.
    token.code = hashlib.sha1(secrets.token_bytes(32)).hexdigest()

    token.access_token = ":".join(
        [
            "AT0",
            "2.0",
            "3.0",
            "720", # lifetime in minutes (possibly)
            token.code[:35],
            str(token.user.persona_id)[-5:],
            token.code[-5:].lower()
        ]
    )

    token.refresh_token = token.access_token
    token.timestamp = time.time()
    token.save()

    response = {
        "code": token.code,
        "lnglv_token": base64.b64encode(token.access_token.encode()).decode(),
    }

    return JsonResponse(response)



@csrf_exempt
def get_token(request):

    # Retrieve token code from url.
    code = request.GET.get("code")
    token = get_object_or_404(DeviceToken, code=code)

    id_token = {
        "aud":"simpsons4-android-client",
        "iss":"http://localhost:8081",
        "iat": int(round(time.time() * 1000)),
        "exp": int(round(time.time() * 1000)) + 86400,
        "pid_id": token.user.pid_id,
        "user_id": token.user.user_id,
        "persona_id": token.user.persona_id,
        "pid_type":"AUTHENTICATOR_ANONYMOUS",
        "auth_time": 0
    }

    #id_token = ".".join(
    #    [
    #        base64.b64encode('{"typ":"JWT","alg":"HS256"}'.encode("utf-8")).decode("utf-8"),
    #        base64.b64encode(
    #            json.dumps(
    #                { 
    #                "aud":"simpsons4-android-client",
    #                "iss":"accounts.ea.com",
    #                "iat": int(round(time.time() * 1000)),
    #                "exp": int(round(time.time() * 1000)) + 3600,
    #                "pid_id": token.user.pid_id,
    #                "user_id": token.user.user_id,
    #                "persona_id": token.user.persona_id,
    #                "pid_type":"AUTHENTICATOR_ANONYMOUS",
    #                "auth_time":0
    #                }
    #            ).encode("utf-8")
    #        ).decode("utf-8"),
    #        base64.b64encode(
    #            bytes.fromhex(
    #                "033b68a1deed4f9724690b1b69923bb719c56395128128dac76066713b1e"
    #            )
    #        ).decode("utf-8")
    #    ]
    #)

    response = {
        "access_token": base64.b64encode(token.access_token.encode()).decode(),
        "token_type": "Bearer",
        "expires_in": int(token.access_token.split(":")[3]),
        "refresh_token": token.access_token,
        "refresh_token_expires_in": int(token.access_token.split(":")[3]),
        "id_token": jwt.encode(id_token, "2Tok8RykmQD41uWDv5mI7JTZ7NIhcZAIPtiBm4Z5", algorithm="HS256")
    }

    return JsonResponse(response)


def tokeninfo(request):

    token = get_object_or_404(DeviceToken, access_token=base64.b64decode(request.headers.get("Access-Token", "").encode()).decode())

    response = {
            "client_id": "simpsons4-android-client",
            "scope": "offline basic.antelope.links.bulk openid signin antelope-rtm-readwrite search.identity basic.antelope basic.identity basic.persona antelope-inbox-readwrite",
            "expires_in": int(token.access_token.split(":")[3]),
            "pid_id": str(token.user.pid_id),
            "pid_type": "AUTHENTICATOR_ANONYMOUS",
            "user_id": str(token.user.user_id),
            "persona_id": token.user.persona_id,
            "authenticators": [
                {
                "authenticator_type": "AUTHENTICATOR_ANONYMOUS",
                "authenticator_pid_id": token.user.pid_id
                }
            ],
            "is_underage": False,
            "stopProcess": "OFF",
            "telemetry_id": str(token.user.telemetry_id)
        }

    return JsonResponse(response)
