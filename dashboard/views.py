from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.core.files.storage import storages
from django.core.files.base import ContentFile
from django.contrib import messages
from django.contrib.auth.views import LoginView, login_required
from django.contrib.auth.models import BaseUserManager

from connect.models import UserId, DeviceToken
from mh.models import LandToken
from proxy.models import ProgRegCode
from proxy.views import get_auth_code, search_friends
from mh.views import save_town, load_town
from avatar.views import get_avatar_url
from friends.views import send_friend_request, cancel_friend_request, accept_friend_request, remove_friend

from .forms import UploadTownForm
from .forms import EditCurrenciesForm
from .forms import RequestUserForm
from .forms import AuthCodeForm
from .forms import ResetPasswordForm
from .forms import UserProfileForm
from .forms import SearchUserForm

from protofiles import LandData_pb2
from operator import itemgetter

import google.protobuf

# Create your views here.

def login(request):

    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("dashboard:index"))

    else:
        return LoginView.as_view(template_name="dashboard/login.html", next_page="dashboard:index")(request)


def register(request):

    register_form = RequestUserForm()

    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("dashboard:index"))

    elif request.method == "POST":

        register_form = RequestUserForm(request.POST)

        if register_form.is_valid():

            email = BaseUserManager.normalize_email(register_form.cleaned_data["email"])

            # Verify if account already exists.
            if UserId.objects.filter(email__iexact=email).exists():
                messages.error(request, "This email is already being used!")

            else:
                get_auth_code(email)
                request.session["auth_email"] = email
                return HttpResponseRedirect(reverse("dashboard:auth"))


    return render(request, "dashboard/register.html", {"register_form": register_form})


def auth(request):

    if not request.session.get("auth_email", False):
        return HttpResponseRedirect(reverse("dashboard:login"))

    elif request.method == "POST":

        auth_form = AuthCodeForm(request.POST)

        if auth_form.is_valid():

            try:
                auth_code = ProgRegCode.objects.get(email=request.session["auth_email"])

            except ProgRegCode.DoesNotExist:
                return HttpResponseRedirect(reverse("dashboard:login"))

            else:

                if auth_form.cleaned_data["code"] == auth_code.code:
                    auth_code.delete()
                    user, _ = UserId.objects.get_or_create(email=request.session["auth_email"], is_registered=True)
                    request.session["auth_username"] = user.username
                    return HttpResponseRedirect(reverse("dashboard:reset_password"))

                else:
                    messages.error(request, "Wrong code.")

    else:
        auth_form = AuthCodeForm()


    return render(request, "dashboard/auth.html", {"auth_form": auth_form, "email": request.session["auth_email"]})


def forgot_password(request):

    forgot_form = RequestUserForm()

    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("dashboard:index"))

    elif request.method == "POST":

        forgot_form = RequestUserForm(request.POST)

        if forgot_form.is_valid():

            email = BaseUserManager.normalize_email(forgot_form.cleaned_data["email"])

            # Verify if account does not exist.
            if not UserId.objects.filter(email__iexact=email).exists():
                messages.error(request, "No account was found with this email.")

            else:
                get_auth_code(email)
                request.session["auth_email"] = email
                return HttpResponseRedirect(reverse("dashboard:auth"))


    return render(request, "dashboard/forgot-password.html", {"forgot_form": forgot_form})


def reset_password(request):

    if not request.session.get("auth_email", False) or not request.session.get("auth_username", False):
        return HttpResponseRedirect(reverse("dashboard:login"))

    elif request.method == "POST":
        password_form = ResetPasswordForm(request.POST)

        if password_form.is_valid():

            # Check if passwords match.
            if password_form.cleaned_data["password"] != password_form.cleaned_data["same_password"]:
                messages.error(request, "The passwords don't match.")

            # Success! Update user password and username (if not empty).
            else:
                user = get_object_or_404(UserId, email=request.session["auth_email"])

                if password_form.cleaned_data["username"] != ".null":
                    user.username = password_form.cleaned_data["username"]

                user.set_password(password_form.cleaned_data["password"])
                user.save(update_fields=["username", "password"])

                # User will have to request a new auth code to be able to revisit the reset password view.
                request.session["auth_email"] = False
                request.session["auth_username"] = False

                return HttpResponseRedirect(reverse("dashboard:login"))

    else:
        password_form = ResetPasswordForm(initial={"username": request.session["auth_username"]})


    return render(request, "dashboard/reset-password.html", {"password_form": password_form})


@login_required(login_url="dashboard:login")
def index(request):

    # Pre-load currencies.
    land_data = LandData_pb2.LandMessage()
    land_data.ParseFromString(load_town(request.user))
    town_form = UploadTownForm()
    currency_form = EditCurrenciesForm(instance=request.user, initial = {"money": land_data.userData.money})

    if request.method == "POST":

        if "town-form" in request.POST:

            town_form = UploadTownForm(request.POST, request.FILES, instance=request.user)
            town_ready = False

            if town_form.is_valid():

                try:
                    land_data.ParseFromString(town_form.cleaned_data["town"].read())

                except google.protobuf.message.DecodeError:
                    # See if this might be a tstole.de backup.
                    try:
                        town_file = town_form.cleaned_data["town"]
                        town_file.seek(0x0c)
                        land_data.ParseFromString(town_file.read())

                    # Reject file
                    except google.protobuf.message.DecodeError:
                        messages.error(request, "Invalid town file!", extra_tags="town")

                    else:
                        town_ready = True

                else:
                    town_ready = True

                if town_ready:
                    mayhem_id = request.user.mayhem_id.int
                    land_data.id = str(mayhem_id)
                    land_data.friendData.name = request.user.username
                    user = town_form.save(commit=False)
                    user.town = ContentFile(land_data.SerializeToString(), f"{mayhem_id}.pb")
                    user.events = bytes()
                    user.save()
                    messages.success(request, "Uploaded town successfuly!", extra_tags="town")
                    LandToken.objects.filter(user=request.user).delete()
                    return HttpResponseRedirect(reverse("dashboard:index"))


        elif "currency-form" in request.POST:

            currency_form = EditCurrenciesForm(request.POST, instance=request.user)

            if currency_form.is_valid():

                # Update town file currencies.
                currencies = currency_form.cleaned_data
                currency_form.save()
                land_data.userData.money = currencies["money"]
                save_town(request.user, land_data)

                # Delete all land tokens.
                LandToken.objects.filter(user=request.user).delete()

                messages.success(request, "Currencies updated!", extra_tags="currency")
                return HttpResponseRedirect(reverse("dashboard:index"))


    context = {
        "town_form": town_form,
        "town_url": reverse("mh:download_protoland", args=(request.user.mayhem_id.int,)),
        "currency_form": currency_form,
        "avatar_url":  get_avatar_url(request.user),
        "avatar_exists": request.user.avatar,
        "username": request.user.username
    }

    return render(request, "dashboard/index.html", context)


@login_required(login_url="dashboard:login")
def profile(request):

    if request.method == "POST":
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user)

        if profile_form.is_valid():

            success = True

            # Update avatar picture if any was uploaded.
            if profile_form.cleaned_data.get("avatar", False):

                avatar_img = profile_form.cleaned_data["avatar"].image
                avatar_ext = avatar_img.format.lower()

                if avatar_ext not in ["png", "jpg"]:
                    messages.error(request, "Image must be either png or jpg.")
                    success = False

                elif avatar_img.width > 416 or avatar_img.height > 416:
                    messages.error(request, "Image dimensions cannot exceed 416x416 pixels.")
                    success = False

                else:
                    request.user.avatar.name = f"{request.user.user_id}.{avatar_ext}"
                    messages.success(request, "Avatar image updated.")


            # Update username if it was edited.
            if profile_form.cleaned_data["username"] != request.user.username:

                if len(profile_form.cleaned_data["username"].strip()) < 5:
                    messages.error(request, "Username must have at least 5 characters.")
                    success = False

                else:
                    request.user.username = profile_form.cleaned_data["username"]
                    request.user.save(update_fields=["username"])
                    messages.success(request, "Username updated.")


            # No errors. Reset the page.
            if success:
                profile_form.save()
                return HttpResponseRedirect(reverse("dashboard:profile"))


    else:
        profile_form = UserProfileForm(instance=request.user)


    context = {
        "profile_form": profile_form,
        "avatar_url": get_avatar_url(request.user),
        "avatar_exists": request.user.avatar,
        "username": request.user.username
    }

    return render(request, "dashboard/profile.html", context)



@login_required(login_url="dashboard:login")
def friends(request):

    search_form = SearchUserForm()
    search_matches = list()

    if request.method == "POST":

        search_form = SearchUserForm(request.POST)
        search_matches = list()

        if search_form.is_valid():

            username = search_form.cleaned_data["search_text"]

            # Sort by alphabetical order.
            search_matches = sorted(
                [
                    {
                        "avatar_url": get_avatar_url(user),
                        "username": user.username,
                        "invite_url": reverse("dashboard:friends_send_request", args=(user.user_id,))

                    } for user in search_friends(request.user, username)
                ],
                key=itemgetter("username")
            )


    # Get pending requests.
    received_requests = sorted(
        [
            {
                "avatar_url": get_avatar_url(invitation.from_user),
                "username": invitation.from_user.username,
                "accept_url": reverse("dashboard:friends_accept_request", args=(invitation.from_user.user_id,)),
                "reject_url": reverse("dashboard:friends_reject_request", args=(invitation.from_user.user_id,))

            } for invitation in request.user.received_invitations.all()
        ],
        key=itemgetter("username")
    )

    sent_requests = sorted(
        [
            {
                "avatar_url": get_avatar_url(invitation.to_user),
                "username": invitation.to_user.username,
                "cancel_url": reverse("dashboard:friends_cancel_request", args=(invitation.to_user.user_id,))

            } for invitation in request.user.sent_invitations.all()
        ],
        key=itemgetter("username")
    )

    friends = sorted(
        [
            {
                "avatar_url": get_avatar_url(user),
                "username": user.username,
                "last_active": user.last_authenticated,
                "remove_url": reverse("dashboard:friends_remove", args=(user.user_id,))

            } for user in request.user.friends.all()
        ],
        key=itemgetter("username")
    )



    context = {
        "search_form": search_form,
        "avatar_url":  get_avatar_url(request.user),
        "avatar_exists": request.user.avatar,
        "username": request.user.username,
        "search_matches": search_matches,
        "received_requests": received_requests,
        "sent_requests": sent_requests,
        "friends": friends
    }

    return render(request, "dashboard/friends.html", context)


@login_required(login_url="dashboard:login")
def friends_send_request(request, to_user_id):
    from_user = request.user
    to_user = get_object_or_404(UserId, user_id=to_user_id)
    return send_friend_request(from_user, to_user, HttpResponseRedirect(reverse("dashboard:friends")))


@login_required(login_url="dashboard:login")
def friends_cancel_request(request, to_user_id):
    from_user = request.user
    to_user = get_object_or_404(UserId, user_id=to_user_id)
    return cancel_friend_request(from_user, to_user, HttpResponseRedirect(reverse("dashboard:friends")))


@login_required(login_url="dashboard:login")
def friends_accept_request(request, from_user_id):
    from_user = get_object_or_404(UserId, user_id=from_user_id)
    to_user = request.user
    return accept_friend_request(from_user, to_user, HttpResponseRedirect(reverse("dashboard:friends")))


@login_required(login_url="dashboard:login")
def friends_reject_request(request, from_user_id):
    from_user = get_object_or_404(UserId, user_id=from_user_id)
    to_user = request.user
    return cancel_friend_request(from_user, to_user, HttpResponseRedirect(reverse("dashboard:friends")))


@login_required(login_url="dashboard:login")
def friends_remove(request, to_user_id):
    from_user = request.user
    to_user = get_object_or_404(UserId, user_id=to_user_id)
    return remove_friend(from_user, to_user, HttpResponseRedirect(reverse("dashboard:friends")))


@login_required(login_url="dashboard:login")
def devices(request):

    user_devices = [
        {
            "manufacturer": token.manufacturer,
            "model": token.device_model,
            "last_active": token.timestamp,
            "remove_url": reverse("dashboard:remove_device", args=(token.advertising_id,))
        } for token in request.user.devicetoken_set.all()
    ]

    context = {
        "avatar_url":  get_avatar_url(request.user),
        "avatar_exists": request.user.avatar,
        "username": request.user.username,
        "devices": user_devices
    }

    return render(request, "dashboard/devices.html", context)


@login_required(login_url="dashboard:login")
def remove_device(request, advertising_id):
    get_object_or_404(DeviceToken, advertising_id=advertising_id).delete()
    return HttpResponseRedirect(reverse("dashboard:devices"))
