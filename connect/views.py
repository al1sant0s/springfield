from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import BaseUserManager
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from proxy.models import ProgRegCode
from proxy.views import get_auth_code

from .models import UserId, DeviceToken

import math
import json
import jwt
import base64
import hashlib
import uuid
import time
import secrets


# Create your views here.
def auth(request, device_id):

    # Give everything the exact same time.
    timestamp = timezone.now()

    # Anonymous login or normal user registration.
    # Try to get sig from URL.
    sig = request.GET.get("sig")
    if sig is not None:

        # Read sig for further authentication.
        jsondata = sig.split(".")[0]
        jsondata += "=" * (math.ceil(len(jsondata) / 64) * 64 - len(jsondata))
        jsondata = json.loads(base64.b64decode(jsondata))

        # Anonymous login.
        if request.GET.get("authenticator_login_type") == "mobile_anonymous":

            # Look up for advertisingId in database.
            advertising_id = uuid.uuid5(uuid.NAMESPACE_OID, jsondata["advertisingId"])

            # Grab existing DeviceToken. If it does not exist, make one.
            try:
                token = DeviceToken.objects.get(advertising_id=advertising_id)

            # Each new token creates a new user.
            except DeviceToken.DoesNotExist:
                token = DeviceToken(
                    advertising_id=advertising_id,
                    user = UserId(),
                    device_id = device_id,
                    device_id_cache = device_id,
                    session_key = secrets.token_urlsafe(32),
                    timestamp = timestamp
                )

            else:
                if token.device_id != device_id:
                    token.device_id_cache = token.device_id
                    token.device_id = device_id

                token.timestamp = timestamp
                token.session_key = secrets.token_urlsafe(32)


            token.user.session_key = token.session_key
            token.user.last_authenticated = timestamp
            token.user.save()

            # Generate new code and new access token.
            token.code = hashlib.sha1(secrets.token_bytes(32)).hexdigest()

            token.access_token = ":".join(
                [
                    "AT0",
                    "2.0",
                    "3.0",
                    "720", # lifetime in minutes (possibly)
                    token.code[:17],
                    str(token.user.persona_id)[-5:],
                    token.code[-5:].lower()
                ]
            )
            token.refresh_token = token.access_token.replace("AT0", "RT0")

            token.access_token = base64.b64encode(token.access_token.encode()).decode()
            token.refresh_token = base64.b64encode(token.access_token.encode()).decode()
            token.save()

            response = {
                "code": token.code,
                "lnglv_token": token.access_token
            }

            return JsonResponse(response)


        # Normal user registration.
        else:

            auth_code = get_object_or_404(
                ProgRegCode,
                email=BaseUserManager.normalize_email(jsondata["email"]),
                code=jsondata["cred"],
                token=get_object_or_404(DeviceToken, device_id=device_id)
            )

            # Found the auth_code?! Great, now look for user with this email.
            try:
                auth_code.token.user = UserId.objects.get(email=auth_code.email)

            # If a user with this email does not exist, it means we have to update the current user email associated with the token.
            # However, if our user is already registered, then we need to create a new user.
            except UserId.DoesNotExist:
                if auth_code.token.user.is_registered:
                    auth_code.token.user = UserId()


            auth_code.token.user.email = auth_code.email
            auth_code.token.user.is_registered = True
            auth_code.token.user.session_key = secrets.token_urlsafe(32)
            auth_code.token.user.last_authenticated = timestamp
            auth_code.token.user.save()

            auth_code.token.session_key = auth_code.token.user.session_key
            auth_code.token.timestamp = timestamp
            auth_code.token.login_status = True
            auth_code.token.save()

            response = {
                "code": auth_code.token.code,
                "lnglv_token": auth_code.token.access_token
            }

            auth_code.delete()
            return JsonResponse(response)

    else:

        token = get_object_or_404(DeviceToken, device_id=device_id)
        email = request.GET.get("email")

        if email is None:

            response = {
                "code": token.code,
                "lnglv_token": token.access_token
            }

            return JsonResponse(response)

        else:

            # Same code as progreg_code view.
            get_auth_code(
                BaseUserManager.normalize_email(email),
                token
            )

            return JsonResponse({"error_description": "REQUIRE_PASSWORD_OR_CODE"})


@csrf_exempt
def get_token(request, device_id):

    token = get_object_or_404(DeviceToken, device_id=device_id)
    pid_type = ["AUTHENTICATOR_ANONYMOUS", "NUCLEUS"]

    id_token = {
        "aud":"simpsons4-android-client",
        "iss":"accounts.ea.com",
        "iat": int(round(time.time() * 1000)),
        "exp": int(round(time.time() * 1000)) + 40630,
        "pid_id": token.user.pid_id,
        "user_id": token.user.user_id,
        "persona_id": token.user.persona_id,
        "pid_type": pid_type[token.login_status],
        "auth_time": 0
    }

    response = {
        "access_token": token.access_token,
        "token_type": "Bearer",
        "expires_in": 40630,
        "refresh_token": token.refresh_token + "." + token.code[:27],
        "refresh_token_expires_in": 40630,
        "id_token": jwt.encode(id_token, "2Tok8RykmQD41uWDv5mI7JTZ7NIhcZAIPtiBm4Z5", algorithm="HS256")
    }

    if request.GET.get("authenticator_type", "") == "NUCLEUS" and request.GET.get("grant_type", "") == "remove_authenticator":
        token.login_status = False
        token.save(update_fields=["login_status"])

    return JsonResponse(response)


def tokeninfo(request, device_id):

    access_token = request.GET.get("access_token")
    token = get_object_or_404(DeviceToken, Q(access_token=access_token) | Q(device_id=device_id) | Q(device_id_cache=device_id))

    response = {
        "client_id": "simpsons4-android-client",
        "scope": "offline basic.antelope.links.bulk openid signin antelope-rtm-readwrite search.identity basic.antelope basic.identity basic.persona antelope-inbox-readwrite",
        "expires_in": 4084253,
        "pid_id": str(token.user.pid_id),
        "pid_type": "AUTHENTICATOR_ANONYMOUS",
        "user_id": str(token.user.user_id),
        "persona_id": token.user.persona_id,
        "authenticators": [
            {
            "authenticator_type": "AUTHENTICATOR_ANONYMOUS",
            "authenticator_pid_id": token.user.pid_id
            },
        ],
        "is_underage": False,
        "stopProcess": "OFF",
        "telemetry_id": str(token.user.telemetry_id),
    }


    if token.login_status:
        response["authenticators"].append(
            {
                "authenticator_type": "NUCLEUS",
                "authenticator_pid_id": token.user.pid_id
            }
        )

    if token.device_id != device_id:
        token.device_id_cache = token.device_id
        token.device_id = device_id
        token.save(update_fields=["device_id_cache", "device_id"])

    return JsonResponse(response)


def probe(request, device_id):
    return HttpResponse()
