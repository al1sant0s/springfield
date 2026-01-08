from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

import xml.etree.ElementTree as ET
import time


def get_current_time(request):
    root = ET.Element("Time")
    ET.SubElement(root, "epochMilliseconds").text = str(int(time.time() * 1000))
    return HttpResponse(ET.tostring(root, "utf8", "xml"), content_type="application/xml")


@csrf_exempt
def trackinglog(request):
    root = ET.Element("Resources")
    ET.SubElement(root, "URI").text = "OK"
    return HttpResponse(ET.tostring(root, "utf8", "xml"), content_type="application/xml")
