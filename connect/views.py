from re import DEBUG
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import BaseUserManager
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from proxy.models import ProgRegCode

from .models import UserId, DeviceToken

import math
import json
import jwt
import base64
import hashlib
import uuid
import time
import datetime
import random
import secrets


def make_user(base_persona_id):

    try:
        last_user = UserId.objects.latest("id")
    except UserId.DoesNotExist:
        user = UserId(persona_id = base_persona_id)
    else:
        user = UserId(persona_id = last_user.persona_id + 1)

    # Set each entry in the database accordingly except mayhem_id and land_token which
    # Django will produce values by itself with the default argument specified in models.
    user.username = f"anon{str(user.persona_id)[-5:]}"
    user.reset_password() # Random password.
    user.email = f"user_{str(user.mayhem_id.int)}@tsto.app"
    user.user_id = user.persona_id + 20000000000
    user.pid_id = user.user_id + 200000
    user.telemetry_id = user.pid_id + 20000000000

    return user


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

            except DeviceToken.DoesNotExist:
                # Each new token creates a new user.
                token = DeviceToken(advertising_id=advertising_id)
                token.user = make_user(1001000000001)
                token.device_id_cache = device_id

            else:
                # Difference between UserID and DeviceToken session_keys means user is logging in another device.
                # Do something about it.
                if token.user.session_key != token.session_key:
                    pass

                token.device_id_cache = token.device_id


            token.user.session_key = secrets.token_urlsafe(32)
            token.user.last_authenticated = timestamp
            token.user.save()

            token.device_id = device_id
            token.session_key = token.user.session_key
            token.timestamp = timestamp

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

            auth_code = get_object_or_404(ProgRegCode, email=str(jsondata["email"]), code=int(str(jsondata["cred"])))

            # Found the auth_code?! Great, now look for user with this email.
            try:
                user = UserId.objects.get(email=jsondata["email"])

            # If a user with this email does not exist, it means we have to update the current user email associated with the token.
            # However, if our user is already registered, then we need to create a new user.
            except UserId.DoesNotExist:
                if auth_code.token.user.is_registered:
                    user = make_user(1001000000001)
                    user.email = jsondata["email"]
                    user.normalize_email()

                else:
                    user = auth_code.token.user
                    user.email = jsondata["email"]
                    user.normalize_email()


            user.is_registered = True
            user.session_key = secrets.token_urlsafe(32)
            user.last_authenticated = timestamp
            user.save()

            auth_code.token.user = user
            auth_code.token.session_key = user.session_key
            auth_code.token.timestamp = user.last_authenticated
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
        #return JsonResponse({"code": hashlib.sha1(secrets.token_bytes(32)).hexdigest()})
        #return JsonResponse({"error":"invalid_request","error_description": "REQUIRE_PASSWORD_OR_CODE", "error_number": 100119})

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
            email = BaseUserManager.normalize_email(email)


            # Search for current active code in database.
            # If it cannot find one, create a new one.
            try:
                auth_code = ProgRegCode.objects.get(email=email)

            except ProgRegCode.DoesNotExist:
                ProgRegCode.objects.create(
                    email=email,
                    code=random.randint(100000, 999999),
                    expiry_on=timezone.now() + datetime.timedelta(hours=2),
                    token=token
                )

            else:
                if auth_code.expiry_on < timezone.now():
                    auth_code.delete()
                    ProgRegCode.objects.create(email=email, expiry_on=timezone.now() + datetime.timedelta(hours=2), token=token)


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
        token.save()

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
        token.save()

    return JsonResponse(response)


def probe(request, device_id):
    return HttpResponse("")
