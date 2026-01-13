from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Create your views here.
def outbound(request, user_id):
    response = {
        "entries":[],
        "pagingInfo": {
            "size": 0,
            "offset": 0, 
            "totalSize":0
        }
    }

    return JsonResponse(response)

@csrf_exempt
def outbound_sent(request, user_id, pid_id):
    return HttpResponse("", status=204)


def inbound(request, user_id):
    response = {
        "entries": [
            {
                "timestamp": 1730568876195,
                "userId":1014813928340,
                "dateTime":"2024-11-02T17:34:36.195Z",
                "inviteTags": {"invite_surface": "unknown"},
                "userType": "NUCLEUS_USER",
                "displayName": "TopDonuts",
                "personaId": 1007225728340,
                "nickName": "TopDonuts"
            }
        ],
        "pagingInfo": {
            "size": 1,
            "offset": 0,
            "totalSize":1
        }
    }

    return JsonResponse(response)
