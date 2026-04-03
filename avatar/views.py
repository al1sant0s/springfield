from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.core.cache import cache

from connect.models import UserId, DeviceToken
from springfield.settings import env

from pathlib import Path
import xml.etree.ElementTree as ET
import json


def get_avatar_filename(user_id):

    avatar_dir = cache.get("avatar_dir")

    if avatar_dir is None:
        with open("config.json", "r") as f:
            config = json.load(f)
            avatar_dir = config["avatar_dir"]
            cache.set("avatar_dir", avatar_dir, timeout = config["cache_seconds"])

    return Path(avatar_dir, f"{user_id}.png")


def get_avatar_url(user):

    static_url = cache.get("static_url")

    if static_url is None:
        protocol = env("PROTOCOL")
        host = env("HOST")
        port = env("PORT")
        static_location = env("STATIC_LOCATION", default="/data/static/")
        static_url = f"{protocol}://{host}:{port}/{static_location.strip('/')}"
        cache.set("static_url", static_url, timeout = env("CACHE_SECONDS", default=3600))

    return f"{static_url}/{user.avatar.name}"


# Create your views here.

def get_avatar(request):

    access_token = request.headers.get("AuthToken")

    if access_token is not None:
        user = get_object_or_404(DeviceToken, access_token=access_token).user
        return get_avatars(request, str(user.user_id))

    else:
        raise Http404


def get_avatars(request, users_ids):

    root = ET.Element("users")

    for user_id in users_ids.split(";"):

        root = ET.SubElement(root, "user")
        ET.SubElement(root, "userId").text = user_id

        avatar = ET.SubElement(user, "avatar")
        ET.SubElement(avatar, "avatarId").text = user_id

        try:
            user = UserId.objects.get(user_id=int(user_id))

        except UserId.DoesNotExist():
            ET.SubElement(avatar, "link").text = ""

        else:
            ET.SubElement(avatar, "link").text = get_avatar_url(user)


    return HttpResponse(ET.tostring(root, "utf8", "xml"), content_type="application/xml")
