import mimetypes
import urllib.parse
import xml.etree.ElementTree as ET
from django.db import models
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from connect.models import UserId, DeviceToken


def download_avatar(request, user_id):
    user = get_object_or_404(
        UserId, models.Q(user_id=user_id) | models.Q(persona_id=user_id)
    )
    if not user.avatar:
        raise Http404

    parsed = urllib.parse.urlsplit(user.avatar.url)
    redirect = parsed.path
    if parsed.scheme and parsed.query:
        redirect += "?" + parsed.query

    # When running behind Nginx, let Nginx serve the file directly.
    content_type = mimetypes.guess_type(user.avatar.name)[0] or "image/png"
    response = HttpResponse(content_type=content_type)
    response["X-Accel-Redirect"] = redirect
    return response


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
        user_id = user_id.strip()
        if not user_id:
            continue

        user_elem = ET.SubElement(root, "user")
        ET.SubElement(user_elem, "userId").text = user_id

        avatar_elem = ET.SubElement(user_elem, "avatar")
        ET.SubElement(avatar_elem, "avatarId").text = user_id

        link_text = request.build_absolute_uri(
            reverse("avatar:download_avatar", args=(user_id,))
        )
        ET.SubElement(avatar_elem, "link").text = link_text

    return HttpResponse(
        ET.tostring(root, "utf8", "xml"), content_type="application/xml"
    )
