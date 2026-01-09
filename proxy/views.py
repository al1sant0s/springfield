from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from connect.models import UserId

import base64
import hashlib

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


def me_persona(request, persona_id):

    user = get_object_or_404(UserId, persona_id = persona_id)

    response = {
        "persona": {
            "personaId": persona_id,
            "pidId": user.pid_id,
            "displayName": user.username,
            "name": user.username.lower(),
            "namespaceName": "gsp-redcrow-simpsons4",
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


def me_personas(request):

    response = {
        "personas": {
            "persona": [
                {
                    "personaId": "1001000000001",
                    "pidId": "1021000200001",
                    "displayName": "user",
                    "name": "user",
                    "namespaceName": "cem_ea_id",
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

    return JsonResponse(response)
