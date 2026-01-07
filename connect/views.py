from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pathlib import Path

import base64
import json
import hashlib
import secrets
import time

# Create your views here.
code = hashlib.sha1(secrets.token_bytes(32)).hexdigest()
lifetime = 86400
pid = "47082"
access_token = [
    "AT0",
    "2.0",
    "3.0",
    str(lifetime),
    code[:35],
    pid[-5:],
    "riqac"
]

def auth(request):

    response = {
        "code": code,
        "lnglv_token": base64.b64encode(":".join(access_token).encode()).decode()
    }

    return JsonResponse(response)




@csrf_exempt
def get_token(request):

    id_token = [
        base64.b64encode('{"typ":"JWT","alg":"HS256"}'.encode("utf-8")).decode("utf-8"),
        base64.b64encode(
            json.dumps(
                { 
                "aud":"simpsons4-ios-client",
                "iss":"accounts.ea.com",
                "iat": int(round(time.time() * 1000)),
                "exp": int(round(time.time() * 1000)) + 3600,
                "pid_id": 100000099999,
                "user_id": 100000099999,
                "persona_id": 100000099999,
                "pid_type":"AUTHENTICATOR_ANONYMOUS",
                "auth_time":0
                }
            ).encode("utf-8")
        ).decode("utf-8"),
        base64.b64encode(
            bytes.fromhex(
                "033b68a1deed4f9724690b1b69923bb719c56395128128dac76066713b1e"
            )
            ).decode("utf-8")
    ]

    response = {
        "access_token": base64.b64encode(":".join(access_token).encode()).decode(),
        "token_type": "Bearer",
        "expires_in": 86400,     # 43199,
        "refresh_token": "",
        "refresh_token_expires_in": 86400, # 86399
        "id_token": id_token
    }

    return JsonResponse(response)
