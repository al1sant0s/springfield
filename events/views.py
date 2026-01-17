from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

# Create your views here.

@require_POST
@csrf_exempt
def pinEvents(request, device_id):
    return JsonResponse({"status": "ok"})


@require_POST
@csrf_exempt
def logEvent(request):

    response = {
        "status": "ok"
    }

    return JsonResponse(response)
