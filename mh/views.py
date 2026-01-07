from django.db.models import F
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views import generic
from django.views.decorators.csrf import csrf_exempt

import xml.etree.ElementTree as ET
import time


def get_current_time(request):
    root = ET.Element("Time")
    ET.SubElement(root, "epochMilliseconds").text = str(int(time.time() * 1000))
    return HttpResponse(ET.tostring(root, "utf8", "xml"))


@csrf_exempt
def trackinglog(request):
    root = ET.Element("Resources")
    ET.SubElement(root, "URI").text = "OK"
    return HttpResponse(ET.tostring(root, "utf8", "xml"))
