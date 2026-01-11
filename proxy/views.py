from django.utils import timezone
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from connect.models import UserId, DeviceToken
from .models import ProgRegCode

import base64
import hashlib
import json
import datetime

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

    # Fake response for fake persona_id.
    if persona_id == 1001000000000:
        response = {
            "persona": {
                "personaId": 1001000000000,
                "pidId": 1021000000000,
                "displayName": "fakeuser",
                "name": "fakeuser",
                "namespaceName": "cem_ea_id",
                "isVisible": True,
                "status": "ACTIVE",
                "statusReasonCode": "",
                "showPersona": "EVERYONE",
                "dateCreated": "2024-10-06T11:3Z",
                "lastAuthenticated": "2024-10-08T11:35Z",
                "anonymousId": "1"
            }
        }

    else:

        user = get_object_or_404(UserId, persona_id = persona_id)

        response = {
            "persona": {
                "personaId": persona_id,
                "pidId": user.pid_id,
                "displayName": user.username,
                "name": user.username.lower(),
                "namespaceName": "cem_ea_id",
                "isVisible": True,
                "status": "ACTIVE",
                "statusReasonCode": "",
                "showPersona": "EVERYONE",
                "dateCreated": user.date_created,
                "lastAuthenticated": user.last_authenticated,
                "anonymousId": base64.b64encode(hashlib.md5(user.username.encode("utf-8")).digest()).decode("utf-8")
            }
        }

    return JsonResponse(response)


def personas(request):
    return JsonResponse({"error":"not_found","error_description":"no mediator found"})


def user_id_personas(request, user_id):

    try:
        user = UserId.objects.get(user_id = user_id)

    except UserId.DoesNotExist:
        response = {
            "personas": {
                "persona": [
                    {
                        "personaId": "1001000000000",
                        "pidId": "1021000200000",
                        "displayName": "user",
                        "name": "user",
                        "namespaceName": "gsp-redcrow-simpsons4",
                        "isVisible": True,
                        "status": "ACTIVE",
                        "statusReasonCode": "",
                        "showPersona": "FRIENDS",
                        "dateCreated": "2024-12-25T0:00Z",
                        "lastAuthenticated": ""
                    }
                ]
            }
        }

    else:
        response = {
            "personas": {
                "persona": [
                    {
                        "personaId": str(user.persona_id),
                        "pidId": str(user.pid_id),
                        "displayName": str(user.username),
                        "name": str(user.username),
                        "namespaceName": "gsp-redcrow-simpsons4",
                        "isVisible": True,
                        "status": "ACTIVE",
                        "statusReasonCode": "",
                        "showPersona": "FRIENDS",
                        "dateCreated": str(user.date_created),
                        "lastAuthenticated": str(user.last_authenticated),
                    }
                ]
            }
        }

    return JsonResponse(response)


@csrf_exempt
def progreg_code(request):

    try:
        json_data = json.loads(request.body)

    except json.JSONDecodeError as e:
        return HttpResponseBadRequest(f"Invalid JSON data: {e}")

    else:

        if json_data["codeType"].lower() == "email":
            email = json_data["email"]

            # Get token from header.
            authorization = request.headers.get("Authorization")

            if authorization is None:
                return HttpResponseBadRequest("Missing Authorization header")

            token = get_object_or_404(DeviceToken, access_token = authorization.split(" ")[1])

            # Search for current active code in database.
            # If it cannot find one, create a new one.
            try:
                auth_code = ProgRegCode.objects.get(email=email)

            except ProgRegCode.DoesNotExist:
                ProgRegCode.objects.create(email=email, expiry_on=timezone.now() + datetime.timedelta(hours=2), token=token)

            else:
                if auth_code.expiry_on < timezone.now():
                    auth_code.delete()
                    ProgRegCode.objects.create(email=email, expiry_on=timezone.now() + datetime.timedelta(hours=2), token=token)

            finally:
                return HttpResponse("")

        else:
            return HttpResponseBadRequest("Only email login is supported.")


def links(request):

    # Get token from header.
    authorization = request.headers.get("Authorization")

    if authorization is None:
        return HttpResponseBadRequest("Missing Authorization header")

    response = {}

    # User logging out, just give anything to pass.
    if authorization == "Bearer":

        response = {
            "pidGamePersonaMappings": {
                "pidGamePersonaMapping": [
                    {
                        "newCreated": False,
                        "personaId": 100100000000,
                        "personaNamespace": request.GET.get("personaNamespace", "gsp-redcrow-simpsons4"),
                        "pidGamePersonaMappingId": 100100000000,
                        "pidId": 1021000200000,
                        "status":"ACTIVE"
                    }
                ]
            }
        }

    else:

        token = get_object_or_404(DeviceToken, access_token = authorization.split(" ")[-1])

        response = {
            "pidGamePersonaMappings": {
                "pidGamePersonaMapping": [
                    {
                        "newCreated": False,
                        "personaId": token.user.persona_id,
                        "personaNamespace": request.GET.get("personaNamespace", "cem_ea_id"),
                        "pidGamePersonaMappingId": token.user.persona_id,
                        "pidId": token.user.pid_id,
                        "status":"ACTIVE"
                    }
                ]
            }
        }

    return JsonResponse(response)
