import xml.etree.ElementTree as ET
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from connect.models import UserId, DeviceToken

# Create your views here.


def get_avatar(request):
    access_token = request.headers.get("AuthToken")

    if access_token is not None:
        user = get_object_or_404(
            DeviceToken.objects.select_related("user"), access_token=access_token
        ).user
        return get_avatars(request, str(user.user_id))

    else:
        raise Http404


def get_avatars(request, users_ids):
    root = ET.Element("users")

    for user_id in users_ids.split(";"):
        user = ET.SubElement(root, "user")
        ET.SubElement(user, "userId").text = user_id

        avatar = ET.SubElement(user, "avatar")
        ET.SubElement(avatar, "avatarId").text = user_id

        try:
            user = UserId.objects.get(user_id=int(user_id))

        except UserId.DoesNotExist:
            ET.SubElement(avatar, "link").text = ""

        else:
            ET.SubElement(avatar, "link").text = user.avatar.url

    return HttpResponse(
        ET.tostring(root, "utf8", "xml"), content_type="application/xml"
    )
