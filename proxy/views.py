from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.cache import cache
from django.contrib.auth.models import BaseUserManager

from springfield.settings import env
from connect.models import UserId, DeviceToken
from friends.models import FriendInvitation
from .models import ProgRegCode

import base64
import hashlib
import json
import datetime
import requests


def search_friends(user, search_username):
    # Do not show ourselves. Neither show non registered users and users that are already our friends.
    # Also hide superusers. Finally, do not show users whose have sent or received a friend request from us.
    friend_query_set = FriendInvitation.objects.filter(
        Q(from_user__in=[user]) | Q(to_user__in=[user])
    )

    users = UserId.objects.filter(
        (
            Q(username__icontains=search_username) |
            Q(email__icontains=search_username)
        ) &
        Q(is_registered=True) &
        Q(is_superuser=False)
    ).exclude(
        id=user.id
    ).exclude(
        friends__in=[user]
    ).exclude(
        sent_invitations__in=friend_query_set
    ).exclude(
        received_invitations__in=friend_query_set
    )

    return users


def check_tsto_api():

    tsto_api_available = cache.get("tsto_api_available")

    if tsto_api_available is None:

        tsto_api_key = env("TSTO_API_KEY")
        tsto_api_team_name = env("TSTO_API_TEAM_NAME")
        response = requests.get("https://tsto.app/api/handshake/", params={"apikey": tsto_api_key})
        timeout = env("CACHE_SECONDS", default=3600)

        if response.status_code == 200 and response.json().get("valid", False):
            tsto_api_available = True
            cache.set("tsto_api_available", tsto_api_available, timeout=timeout)
            cache.set("tsto_api_key", tsto_api_key, timeout=timeout)
            cache.set("tsto_api_team_name", tsto_api_team_name, timeout=timeout)

        else:
            cache.set("tsto_api_available", False, timeout=timeout)


    return tsto_api_available


def get_auth_code(email, use_tsto_api=True):

    # If a non expired auth code exists in the database already use it.
    # Otherwise get a new code.
    auth_code_queryset = ProgRegCode.objects.filter(email=email)
    if auth_code_queryset.exists() and auth_code_queryset.first().expiry_on < timezone.now():
        return auth_code_queryset.first()

    else:
        code = get_random_string(6, allowed_chars="0123456789")

        # Get code from TSTO API if available.
        if use_tsto_api and check_tsto_api():

            try:
                user = UserId.objects.get(email=email)

            except UserId.DoesNotExist:
                username = "user"

            else:
                username = user.username

            response = requests.post("https://tsto.app/api/auth/sendCode/",
                params={
                    "apikey": cache.get("tsto_api_key"),
                    "emailAddress": email,
                    "teamName": cache.get("tsto_api_team_name"),
                    "username": username
                }
            )

            if response.status_code == 200:
                content = response.json()

                if content["status"] == 200:
                    code = content["code"]


        # Search for current active code in database.
        # If it cannot find one, create a new one.
        auth_code, created = ProgRegCode.objects.get_or_create(
            email=email,
            defaults={
                "code": code,
                "expiry_on": timezone.now() + datetime.timedelta(minutes=30)
            }
        )

        if not created:
            auth_code.code = code,
            auth_code.expiry_on = timezone.now() + datetime.timedelta(minutes=30)
            auth_code.save()


        return auth_code


# Create your views here.

def geoagerequirements(request):
    response = {
        "geoAgeRequirements": {
            "minLegalRegAge": 13,
            "minAgeWithConsent": "3",
            "minLegalContactAge": 13,
            "country": "US"
        }
    }
    return JsonResponse(response)


def me_personas(request, persona_id):
    user = get_object_or_404(UserId, persona_id=persona_id)
    response = {
        "persona": {
            "personaId": user.persona_id,
            "pidId": user.user_id,
            "displayName": user.username,
            "name": user.username,
            "namespaceName": "gsp-redcrow-simpsons4",
            "isVisible": True,
            "status": "ACTIVE",
            "statusReasonCode": "",
            "showPersona": "EVERYONE",
            "dateCreated": user.date_joined.strftime('%Y-%m-%dT%H:%MZ'),
            "lastAuthenticated": user.last_authenticated.strftime('%Y-%m-%dT%H:%MZ'),
            "anonymousId": base64.b64encode(hashlib.md5(user.username.encode("utf-8")).digest()).decode("utf-8")
        }
    }
    return JsonResponse(response)


def pids_personas(request):
    return JsonResponse({"error":"not_found","error_description":"no mediator found"})


def user_id_personas(request, user_id):
    user = get_object_or_404(DeviceToken, access_token=request.headers.get("Authorization", "").split(" ")[-1]).user
    response = {
        "personas": {
            "persona": [
                {
                    "personaId": user.persona_id,
                    "pidId": user.user_id,
                    "displayName": user.username,
                    "name": user.username,
                    "namespaceName": "gsp-redcrow-simpsons4",
                    "isVisible": True,
                    "status": "ACTIVE",
                    "statusReasonCode": "",
                    "showPersona": "FRIENDS",
                    "dateCreated": user.date_joined.strftime('%Y-%m-%dT%H:%MZ'),
                    "lastAuthenticated": user.last_authenticated.strftime('%Y-%m-%dT%H:%MZ'),
                }
            ]
        }
    }
    return JsonResponse(response)


def personas(request):

    friends = list()
    username = request.GET.get("displayName")

    if username is None:
        return HttpResponseBadRequest("Missing displayName in URL!")

    elif len(username) < 6:
        return HttpResponseBadRequest("DisplayName is too short!")

    elif username.endswith("*"):
        username = username[:-1]


    our_user = get_object_or_404(DeviceToken, access_token=request.headers.get("Authorization", "").split(" ")[-1]).user

    for user in search_friends(our_user, username):

        friends.append(
            {
                "personaId": user.persona_id,
                "pidId": user.user_id,
                "displayName": user.username,
                "name": user.username,
                "namespaceName": request.GET.get("namespaceName", "gsp-redcrow-simpsons4"),
                "isVisible": True,
                "status": "ACTIVE",
                "statusReasonCode": "",
                "showPersona": "NO_ONE",
                "dateCreated": user.date_joined.strftime('%Y-%m-%dT%H:%MZ'),
                "lastAuthenticated": user.last_authenticated.strftime('%Y-%m-%dT%H:%MZ'),
            }
        )

    return JsonResponse({"personas": {"persona": friends}})


@csrf_exempt
@require_POST
def progreg_code(request):

    try:
        json_data = json.loads(request.body)

    except json.JSONDecodeError as e:
        return HttpResponseBadRequest(f"Invalid JSON data: {e}")

    else:

        if json_data["codeType"].lower() == "email":
            # Generate auth code.
            get_auth_code(BaseUserManager.normalize_email(json_data["email"]))
            return HttpResponse()

        else:
            return HttpResponseBadRequest("Only email login is supported.")


def links(request):
    token = get_object_or_404(DeviceToken, access_token=request.headers.get("Authorization", "").split(" ")[-1])
    response = {
        "pidGamePersonaMappings": {
            "pidGamePersonaMapping": [
                {
                    "newCreated": False,
                    "personaId": token.user.persona_id,
                    "personaNamespace": request.GET.get("personaNamespace", "gsp-redcrow-simpsons4"),
                    "pidGamePersonaMappingId": token.user.persona_id,
                    "pidId": token.user.user_id,
                    "status":"ACTIVE"
                }
            ]
        }
    }
    return JsonResponse(response)
