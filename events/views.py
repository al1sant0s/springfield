from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Create your views here.

@csrf_exempt
def pinEvents(request):
    return JsonResponse({"status": "ok"})


def probe(request):
    return HttpResponse("")

