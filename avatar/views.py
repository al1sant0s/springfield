from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.core.cache import cache


import xml.etree.ElementTree as ET
import json

from connect.models import UserId, DeviceToken


def get_avatar_url():

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
            cache.set("avatar_dir", config["avatar_dir"])


    return avatar_url


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
        ET.SubElement(avatar, "link").text = f"{get_avatar_url()}/{user_id}.png"


    return HttpResponse(ET.tostring(root, "utf8", "xml"), content_type="application/xml")
