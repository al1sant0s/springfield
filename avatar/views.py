import mimetypes
import urllib.parse
import xml.etree.ElementTree as ET
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from connect.models import UserId, DeviceToken

# Create your views here.


def download_avatar(request, user_id):
    try:
        parsed_id = int(user_id)
        target_user = UserId.objects.filter(
            models.Q(user_id=parsed_id) | models.Q(persona_id=parsed_id)
        ).first()
    except (ValueError, TypeError):
        raise Http404

    if not target_user or not target_user.avatar:
        raise Http404

    content_type = mimetypes.guess_type(target_user.avatar.name)[0] or "image/png"

    # When running behind Nginx, let Nginx serve the file directly.
    # For local filesystem storage the plain media URL is used.
    # For S3/Garage the presigned URL is stripped of its domain so that
    # Nginx can proxy the signed path+query to S3 with the correct Host header.
    if not settings.DEBUG:
        response = HttpResponse(content_type=content_type)
        parsed = urllib.parse.urlsplit(target_user.avatar.url)
        if parsed.scheme:
            # Remote storage — forward signed path + query string
            redirect = parsed.path
            if parsed.query:
                redirect += "?" + parsed.query
        else:
            # Local filesystem — plain relative URL
            redirect = parsed.path
        response["X-Accel-Redirect"] = redirect
        return response

    # Fallback for development (DEBUG=True)
    try:
        return HttpResponse(target_user.avatar.read(), content_type=content_type)
    except Exception:
        raise Http404


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
