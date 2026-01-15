from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.db import models, transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from connect.models import UserId, DeviceToken
from friends.models import FriendInvitation

# Create your views here.
def outbound(request, device_id, user_id):

    # Look up for sent_invitations.
    user = get_object_or_404(DeviceToken, device_id=device_id).user
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
                "level": 45,
            }
        )

    response = {
        "entries": entries,
        "pagingInfo": {
            "size": len(entries),
            "offset": 0,
            "totalSize": len(entries)
        }
    }

    return JsonResponse(response)

@csrf_exempt
def outbound_sent(request, device_id, from_user_id, to_user_id):

    # Get user sending invitation and receiving invitation.
    from_user = get_object_or_404(DeviceToken, device_id=device_id).user
    to_user = get_object_or_404(UserId, user_id=to_user_id)

    if request.method == "DELETE":
        try:
            with transaction.atomic():
                FriendInvitation.objects.filter(
                    models.Q(from_user=to_user, to_user=from_user) |
                    models.Q(from_user=from_user, to_user=to_user)
                ).delete()

        except Exception:
            return HttpResponseBadRequest("Failed to delete friend invitations.")

        else:
            return HttpResponse("", status=204)


    if from_user == to_user:
        return HttpResponseBadRequest("Cannot befriend yourself!")

    try:
        with transaction.atomic():
            # Lock and check for existing invitations.
            exists = FriendInvitation.objects.select_for_update().filter(
                models.Q(from_user=to_user, to_user=from_user) |
                models.Q(from_user=from_user, to_user=to_user)
            ).exists()

            if exists:
                return HttpResponseBadRequest("An invitation already exists between these users.")

            FriendInvitation.objects.create(from_user=from_user, to_user=to_user, invitation_date=timezone.now())
            return HttpResponse("", status=204)

    except Exception:
        return HttpResponseBadRequest("Failed to create invitation.")


def inbound(request, device_id, user_id):

    # Look up for received_invitations.
    user = get_object_or_404(DeviceToken, device_id=device_id).user

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

    response = {
        "entries": entries,
        "pagingInfo": {
            "size": len(entries),
            "offset": 0,
            "totalSize": len(entries)
        }
    }

    return JsonResponse(response)


@csrf_exempt
def inbound_accept(request, device_id, to_user_id, from_user_id):

    # Get user sending invitation and receiving invitation.
    from_user = get_object_or_404(UserId, user_id=from_user_id)
    to_user = get_object_or_404(DeviceToken, device_id=device_id).user

    try:
        with transaction.atomic():
            FriendInvitation.objects.filter(
                models.Q(from_user=to_user, to_user=from_user) |
                models.Q(from_user=from_user, to_user=to_user)
            ).delete()

    except Exception:
        return HttpResponseBadRequest("Failed to delete friend invitations.")

    else:
        if from_user == to_user:
            return HttpResponseBadRequest("Cannot befriend yourself!")

        else:
            to_user.friends.add(from_user)
            to_user.save()
            return HttpResponse("", status=204)


def get_friends(request, device_id, user_id):

    user = get_object_or_404(DeviceToken, device_id=device_id).user
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
                "_friendTyoe": "OLD",
            }
        )

    response = {
        "entries": entries,
        "pagingInfo": {
            "size": len(entries),
            "offset": 0,
            "totalSize": len(entries)
        }
    }

    return JsonResponse(response)


@csrf_exempt
def cancel_friendship(request, device_id, to_user_id, from_user_id):
    from_user = get_object_or_404(DeviceToken, device_id=device_id).user
    to_user = get_object_or_404(UserId, user_id=to_user_id)
    from_user.friends.remove(to_user)
    to_user.friends.remove(from_user)

    return HttpResponse("", status=204)
