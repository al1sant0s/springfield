from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.db import models
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from connect.models import UserId, DeviceToken
from django.contrib.auth.models import BaseUserManager
from friends.models import FriendInvitation
from .models import ProgRegCode

import base64
import hashlib
import json
import datetime


def search_friends(user, search_username):
    # Do not show ourselves. Neither show non registered users and users that are already our friends.
    # Also hide superusers. Finally, do not show users whose have sent or received a friend request from us.
    friend_query_set = FriendInvitation.objects.filter(
        models.Q(from_user__in=[user]) | models.Q(to_user__in=[user])
    )

    users = UserId.objects.filter(
        (
            models.Q(username__icontains=search_username) |
            models.Q(email__icontains=search_username)
        ) &
        models.Q(is_registered=True) &
        models.Q(is_superuser=False)
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


def get_auth_code(email, token):

    # Search for current active code in database.
    # # If it cannot find one, create a new one.
    auth_code, created = ProgRegCode.objects.get_or_create(
        email=email,
        defaults={
            "code": get_random_string(6, allowed_chars="0123456789"),
            "expiry_on": timezone.now() + datetime.timedelta(hours=2),
            "token": token,
        }
    )

    if not created and auth_code.expiry_on < timezone.now():
        auth_code.code = get_random_string(6, allowed_chars="0123456789")
        auth_code.expiry_on = timezone.now() + datetime.timedelta(hours=2)
        auth_code.save()


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

    response = {
        "persona": {
            "personaId": persona_id,
            "pidId": persona_id,
            "displayName": "user",
            "name": "user",
            "namespaceName": "gsp-redcrow-simpsons4",
            "isVisible": True,
            "status": "ACTIVE",
            "statusReasonCode": "",
            "showPersona": "EVERYONE",
            "dateCreated": "2024-10-06T11:3Z",
            "lastAuthenticated": "2024-10-08T11:35Z",
            "anonymousId": "user"
        }
    }

    user = get_object_or_404(UserId, persona_id=persona_id)

    response["persona"].update(
        {
            "personaId": user.persona_id,
            "pidId": user.user_id,
            "displayName": user.username,
            "name": user.username.lower(),
            "dateCreated": user.date_joined.strftime('%Y-%m-%dT%H:%MZ'),
            "lastAuthenticated": user.last_authenticated.strftime('%Y-%m-%dT%H:%MZ'),
            "anonymousId": base64.b64encode(hashlib.md5(user.username.encode("utf-8")).digest()).decode("utf-8")
        }
    )

    return JsonResponse(response)


def pids_personas(request):
    return JsonResponse({"error":"not_found","error_description":"no mediator found"})


def user_id_personas(request, user_id):

    try:
        user = UserId.objects.get(user_id=user_id)

    except UserId.DoesNotExist:
        return JsonResponse({"personas": {"persona": list()}})

    else:
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
            get_auth_code(
                BaseUserManager.normalize_email(json_data["email"]),
                get_object_or_404(DeviceToken, access_token=request.headers.get("Authorization", "").split(" ")[-1])
            )
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
                    "personaNamespace": request.GET.get("personaNamespace", "cem_ea_id"),
                    "pidGamePersonaMappingId": token.user.persona_id,
                    "pidId": token.user.user_id,
                    "status":"ACTIVE"
                }
            ]
        }
    }

    return JsonResponse(response)
