import datetime
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import BaseUserManager
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from proxy.models import ProgRegCode
from proxy.views import get_auth_code

from .models import UserId, DeviceToken
from mh.models import LandToken

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
        json_data = sig.split(".")[0]
        json_data += "=" * (math.ceil(len(json_data) / 64) * 64 - len(json_data))
        json_data = json.loads(base64.b64decode(json_data))

        # Anonymous login.
        if request.GET.get("authenticator_login_type") == "mobile_anonymous":

            # Look up for advertisingId in database.
            advertising_id = uuid.uuid5(uuid.NAMESPACE_OID, json_data["advertisingId"])

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
                email=BaseUserManager.normalize_email(json_data["email"]),
                code=json_data["cred"],
                expiry_on__gt=timestamp
            )

            token = get_object_or_404(DeviceToken, Q(device_id=device_id) | Q(device_id_cache=device_id))
            user = token.user

            # Found the auth_code?! Great, now look for user with this email.
            try:
                token.user = UserId.objects.get(email=auth_code.email)

            # If a user with this email does not exist, it means we have to update the current user email associated with the token.
            # However, if our user is already registered, then we need to create a new user.
            except UserId.DoesNotExist:
                if token.user.is_registered:
                    token.user = UserId()

            token.user.email = auth_code.email
            token.user.is_registered = True
            token.user.session_key = secrets.token_urlsafe(32)
            token.user.last_authenticated = timestamp
            token.user.save()

            token.session_key = token.user.session_key
            token.timestamp = timestamp
            token.login_status = True
            token.save()

            # Point land_token to new user.
            if user != token.user:
                LandToken.objects.filter(user=token.user).delete()
                LandToken.objects.filter(user=user).update(user=token.user)

            response = {
                "code": token.code,
                "lnglv_token": token.access_token
            }

            auth_code.delete()
            return JsonResponse(response)

    else:

        token = get_object_or_404(DeviceToken, Q(device_id=device_id) | Q(device_id_cache=device_id))
        email = request.GET.get("email")

        if email is None:

            response = {
                "code": token.code,
                "lnglv_token": token.access_token
            }

            return JsonResponse(response)

        else:

            # Generate auth code.
            get_auth_code(BaseUserManager.normalize_email(email))

            return JsonResponse({"error_description": "REQUIRE_PASSWORD_OR_CODE"})


@csrf_exempt
def get_token(request, device_id):

    token = get_object_or_404(DeviceToken, Q(device_id=device_id) | Q(device_id_cache=device_id))
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
        # Delete all land tokens.
        LandToken.objects.filter(user=token.user).delete()
        token.login_status = False
        token.save(update_fields=["login_status"])

    return JsonResponse(response)


def tokeninfo(request, device_id):

    access_token = request.GET.get("access_token")
    token = get_object_or_404(DeviceToken, Q(device_id=device_id) | Q(device_id_cache=device_id) | Q(access_token=access_token))

    # Update session keys and timestamps.
    token.user.last_authenticated = timezone.now() 
    token.user.session_key = secrets.token_urlsafe(32)
    token.user.save(update_fields=["last_authenticated", "session_key"])

    token.timestamp = token.user.last_authenticated
    token.session_key = token.user.session_key
    token.save(update_fields=["timestamp", "session_key"])

    # Make a land token if one does not already exist.
    land_token, _ = LandToken.objects.get_or_create(user=token.user)
    land_token.retrieved = False
    land_token.save()

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

    return JsonResponse(response)


def probe(request, device_id):
    return HttpResponse()
