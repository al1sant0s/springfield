import xml.etree.ElementTree as ET
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models
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
        user_id = user_id.strip()
        if not user_id:
            continue

        user_elem = ET.SubElement(root, "user")
        ET.SubElement(user_elem, "userId").text = user_id

        avatar_elem = ET.SubElement(user_elem, "avatar")
        ET.SubElement(avatar_elem, "avatarId").text = user_id

        link_text = ""
        try:
            parsed_id = int(user_id)
            target_user = UserId.objects.filter(
                models.Q(user_id=parsed_id) | models.Q(persona_id=parsed_id)
            ).first()

            if (
                target_user
                and target_user.avatar
                and default_storage.exists(target_user.avatar.name)
            ):
                url = target_user.avatar.url
                if url.startswith("/"):
                    link_text = (
                        f"{settings.SERVER_BASE_URL}{url}"
                        if getattr(settings, "SERVER_BASE_URL", None)
                        else request.build_absolute_uri(url)
                    )
                else:
                    link_text = url

        except (ValueError, TypeError):
            pass

        ET.SubElement(avatar_elem, "link").text = link_text

    return HttpResponse(
        ET.tostring(root, "utf8", "xml"), content_type="application/xml"
    )
