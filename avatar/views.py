from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.core.cache import cache

from connect.models import DeviceToken

from pathlib import Path
import xml.etree.ElementTree as ET
import json




def get_avatar_filename(user_id):

    avatar_dir = cache.get("avatar_dir")

    if avatar_dir is None:

        with open("config.json", "r") as f:

            config = json.load(f)
            avatar_dir = config["avatar_dir"]
            cache.set("avatar_dir", avatar_dir, timeout = config["cache_minutes"])


    return Path(avatar_dir, f"{user_id}.png")


def get_avatar_url(user_id):

    avatar_url = cache.get("avatar_url")

    if avatar_url is None:

        with open("config.json", "r") as f:

            config = json.load(f)
            protocol = config["protocol"]
            host = config["host"]
            port = config["port"]
            avatar_location = config["avatar_location"].removeprefix("/").removesuffix("/")

            avatar_url = f"{protocol}://{host}:{port}/{avatar_location}"
            cache.set("avatar_url", avatar_url, timeout = config["cache_minutes"])


    return f"{avatar_url}/{user_id}.png"


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

        user = ET.SubElement(root, "user")
        ET.SubElement(user, "userId").text = user_id

        avatar = ET.SubElement(user, "avatar")
        ET.SubElement(avatar, "avatarId").text = user_id
        ET.SubElement(avatar, "link").text = get_avatar_url(user_id)


    return HttpResponse(ET.tostring(root, "utf8", "xml"), content_type="application/xml")
