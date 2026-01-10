import email
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from proxy.models import ProgRegCode

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

    sig = request.GET.get("sig")

    if sig is None:
        return HttpResponseBadRequest("Missing required attribute: sig")

    # Read sig for further authentication.
    jsondata = sig.split(".")[0]
    jsondata += "=" * (math.ceil(len(jsondata) / 64) * 64 - len(jsondata))
    jsondata = json.loads(base64.b64decode(jsondata))

    # Anonymous login.
    if request.GET.get("response_type") == "code":

        # Look up for advertisingId in database.
        advertising_id = uuid.uuid5(uuid.NAMESPACE_OID, jsondata["advertisingId"])

        # Give everything the exact same time.
        timestamp = timezone.now()

        # Grab existing DeviceToken. If it does not exist, make one.
        try:
            token = DeviceToken.objects.get(advertising_id=advertising_id)

        except DeviceToken.DoesNotExist:

            token = DeviceToken(advertising_id=advertising_id)

            # Each new token creates a new user.
            try:
                last_user = UserId.objects.latest("id")
            except UserId.DoesNotExist:
                token.user = UserId(persona_id = 1001000000001)
            else:
                token.user = UserId(persona_id = last_user.persona_id + 1)

            # Set each entry in the database accordingly except mayhem_id and land_token which
            # Django will produce values by itself with the default argument specified in models.
            token.user.username = f"anon{str(token.user.persona_id)[-5:]}"
            token.user.reset_password() # Random password.
            token.user.email = f"user_{str(token.user.mayhem_id)}@tsto.app"
            token.user.user_id = token.user.persona_id + 20000000000
            token.user.pid_id = token.user.user_id + 200000
            token.user.telemetry_id = token.user.pid_id + 20000000000
            token.user.date_created = timestamp

        else:
            # Difference between UserID and DeviceToken session_keys means user is logging in another device.
            # Do something about it.
            if token.user.session_key != token.session_key:
                pass



        # Update both user and token session key.
        token.user.session_key = secrets.token_urlsafe(32)
        token.session_key = secrets.token_urlsafe(32)

        # Finally update timestamps in both UserID and DeviceToken.
        token.user.last_authenticated = timestamp
        token.timestamp = timestamp
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

    # Normal user login. No need to refresh the token and the user, just reassociate them with each other.
    elif request.GET.get("response_type") == "code lnglv_token":

        auth_code = get_object_or_404(ProgRegCode, email=jsondata["email"], code=int(str(jsondata["cred"])))

        # Found the auth_code?! Great, now look for user with this email.
        try:
            user = UserId.object.get(email=jsondata["email"])

        # If a user with this email does not exist, it means we have to update the current user email associated with the token.
        except:
            auth_code.token.user.email = jsondata["email"]
            auth_code.token.user.session_key = token.session_key
            auth_code.token.user.save()

        else:
            auth_code.token.user = user
            auth_code.token.user.session_key = auth_code.token.session_key
            auth_code.token.user.save()

        finally:
            auth_code.delete()
            return HttpResponse("Success")

    else:
        return HttpResponseBadRequest(f"URL parameter response_type returned {request.GET.get(response_type)}")



@csrf_exempt
def get_token(request):

    # Retrieve token code from url.
    code = request.GET.get("code")

    if code is None:
        return HttpResponseBadRequest("Missing required attribute: code")


    token = get_object_or_404(DeviceToken, code=code)

    id_token = {
        "aud":"simpsons4-android-client",
        "iss":"accounts.ea.com",
        "iat": int(round(time.time() * 1000)),
        "exp": int(round(time.time() * 1000)) + 86400,
        "pid_id": token.user.pid_id,
        "user_id": token.user.user_id,
        "persona_id": token.user.persona_id,
        "pid_type":"AUTHENTICATOR_ANONYMOUS",
        "auth_time": 0
    }

    response = {
        "access_token": token.access_token,
        "token_type": "Bearer",
        "expires_in": 720,
        "refresh_token": token.refresh_token + "." + token.code[:27],
        "refresh_token_expires_in": 720,
        "id_token": jwt.encode(id_token, "2Tok8RykmQD41uWDv5mI7JTZ7NIhcZAIPtiBm4Z5", algorithm="HS256")
    }

    return JsonResponse(response)


def tokeninfo(request):

    # access_token comes through the URL.
    if request.GET.get("access_token") is not None:

        token = get_object_or_404(DeviceToken, access_token=request.GET.get("access_token", ""))

        response = {
                "client_id": "simpsons4-android-client",
                "scope": "offline basic.antelope.links.bulk openid signin antelope-rtm-readwrite search.identity basic.antelope basic.identity basic.persona antelope-inbox-readwrite",
                "expires_in": 720,
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

    # Token comes through header but we won't accept it as it contains underscores. Give fake response instead.
    else:

        #token = get_object_or_404(DeviceToken, access_token=base64.b64decode(request.headers.get("Access-Token", "").encode()).decode())
        #token = get_object_or_404(DeviceToken.objects.order_by('-id')[:1])

        response = {
                "client_id": "simpsons4-android-client",
                "scope": "offline basic.antelope.links.bulk openid signin antelope-rtm-readwrite search.identity basic.antelope basic.identity basic.persona antelope-inbox-readwrite",
                "expires_in": 720,
                "pid_id": "1021000200000",
                "pid_type": "AUTHENTICATOR_ANONYMOUS",
                "user_id": "1021000000000",
                "persona_id": 1001000000000,
                "authenticators": [
                    {
                    "authenticator_type": "AUTHENTICATOR_ANONYMOUS",
                    "authenticator_pid_id": 1021000200000
                    }
                ],
                "is_underage": False,
                "stopProcess": "OFF",
                "telemetry_id": "1041000200000"
            }


    return JsonResponse(response)
