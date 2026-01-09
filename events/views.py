from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from pathlib import Path

# Create your views here.

@csrf_exempt
def pinEvents(request):
    return JsonResponse({"status": "ok"})


def probe(request):
    return HttpResponse("")


@csrf_exempt
def logEvent(request):

    response = {
        "status": "ok"
    }

    return JsonResponse(response)
