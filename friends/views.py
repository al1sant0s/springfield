from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.db import models, transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_GET, require_POST

from connect.models import UserId, DeviceToken
from friends.models import FriendInvitation


def send_friend_request(from_user, to_user, success_response):

    if from_user == to_user:
        return HttpResponseForbidden("Cannot befriend yourself!")

    try:
        with transaction.atomic():
            # Lock and check for existing invitations.
            exists = FriendInvitation.objects.select_for_update().filter(
                models.Q(from_user=to_user, to_user=from_user) |
                models.Q(from_user=from_user, to_user=to_user)
            ).exists()

            if exists:
                return HttpResponse("An invitation already exists between these users.", status=409)

            FriendInvitation.objects.create(from_user=from_user, to_user=to_user, invitation_date=timezone.now())
            return success_response

    except Exception:
        return HttpResponse("Failed to create invitation.", status=500)


def cancel_friend_request(from_user, to_user, success_response):

    try:
        with transaction.atomic():
            FriendInvitation.objects.filter(
                models.Q(from_user=to_user, to_user=from_user) |
                models.Q(from_user=from_user, to_user=to_user)
            ).delete()

    except Exception:
        return HttpResponse("Failed to delete friend invitations.", status=500)

    else:
        return success_response


def accept_friend_request(from_user, to_user, success_response):

    try:
        with transaction.atomic():
            FriendInvitation.objects.filter(
                models.Q(from_user=to_user, to_user=from_user) |
                models.Q(from_user=from_user, to_user=to_user)
            ).delete()

    except Exception:
        return HttpResponse("Failed to delete friend invitations.", status=500)

    else:
        if from_user == to_user:
            return HttpResponseForbidden("Cannot befriend yourself!")

        else:
            to_user.friends.add(from_user)
            return success_response


def remove_friend(from_user, to_user, success_response):
    from_user.friends.remove(to_user)
    to_user.friends.remove(from_user)
    return success_response


@require_GET
def outbound(request, user_id):

    # Look up for sent_invitations.
    user = get_object_or_404(DeviceToken, access_token=request.headers.get("X-AuthToken")).user
    entries = list()

    for invitation in user.sent_invitations.all():
        entries.append(
            {
                "timestamp": int(invitation.invitation_date.timestamp() * 1000),
                "userId": invitation.to_user.user_id,
                "dateTime": invitation.invitation_date.isoformat(),
                "inviteTags": {"invite_surface": "unknown"},
                "userType": "NUCLEUS_USER",
                "displayName": invitation.to_user.username,
                "personaId": invitation.to_user.persona_id,
                "nickName": invitation.to_user.username,
            }
        )

    n = len(entries)

    response = {
        "entries": entries,
        "pagingInfo": {
            "size": n,
            "offset": 0,
            "totalSize": n
        }
    }

    return JsonResponse(response)


@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def outbound_sent(request, from_user_id, to_user_id):
    # Get user sending invitation and receiving invitation.
    from_user = get_object_or_404(DeviceToken, access_token=request.headers.get("X-AuthToken")).user
    to_user = get_object_or_404(UserId, user_id=to_user_id)

    if request.method == "DELETE":
        return cancel_friend_request(from_user, to_user, HttpResponse(status=204))

    else:
        return send_friend_request(from_user, to_user, HttpResponse(status=204))


@require_GET
def inbound(request, user_id):
    # Look up for received_invitations.
    user = get_object_or_404(DeviceToken, access_token=request.headers.get("X-AuthToken")).user

    entries = list()
    for invitation in user.received_invitations.all():
        entries.append(
            {
                "timestamp": int(invitation.invitation_date.timestamp()),
                "userId": invitation.from_user.user_id,
                "dateTime": invitation.invitation_date.isoformat(),
                "inviteTags": {"invite_surface": "unknown"},
                "userType": "NUCLEUS_USER",
                "displayName": invitation.from_user.username,
                "personaId": invitation.from_user.persona_id,
                "nickName": invitation.from_user.username,
            }
        )

    n = len(entries)

    response = {
        "entries": entries,
        "pagingInfo": {
            "size": n,
            "offset": 0,
            "totalSize": n
        }
    }

    return JsonResponse(response)


@csrf_exempt
@require_POST
def inbound_accept(request, to_user_id, from_user_id):
    # Get user sending invitation and receiving invitation.
    from_user = get_object_or_404(UserId, user_id=from_user_id)
    to_user = get_object_or_404(DeviceToken, access_token=request.headers.get("X-AuthToken")).user
    return accept_friend_request(from_user, to_user, HttpResponse(status=204))


@require_GET
def get_friends(request, user_id):

    user = get_object_or_404(DeviceToken, access_token=request.headers.get("X-AuthToken")).user
    entries = list()

    for friend in user.friends.all():
        entries.append(
            {
                "timestamp": int(timezone.now().timestamp()),
                "friendType": "OLD",
                "userId": friend.user_id,
                "favorite": False,
                "dateTime": timezone.now().isoformat(),
                "edgeAttribute": {
                    "tags": {
                        "friendface": "unknown",
                    }
                },
                "userType": "NUCLEUS_USER",
                "displayName": friend.username,
                "personaId": friend.persona_id,
                "nickName": friend.username,
                "_friendType": "OLD",
            }
        )

    n = len(entries)

    response = {
        "entries": entries,
        "pagingInfo": {
            "size": n,
            "offset": 0,
            "totalSize": n
        }
    }

    return JsonResponse(response)


@csrf_exempt
@require_http_methods(["DELETE"])
def cancel_friendship(request, to_user_id, from_user_id):
    from_user = get_object_or_404(DeviceToken, access_token=request.headers.get("X-AuthToken")).user
    to_user = get_object_or_404(UserId, user_id=to_user_id)
    return remove_friend(from_user, to_user, HttpResponse(status=204))
