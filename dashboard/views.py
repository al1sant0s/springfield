from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.db import models
from django.contrib import messages
from django.contrib.auth.views import LoginView, login_required
from django.contrib.auth.models import BaseUserManager
from django.forms import formset_factory

from connect.models import UserId, DeviceToken
from mh.models import LandToken
from proxy.models import ProgRegCode
from proxy.views import get_auth_code, personas, search_friends
from mh.views import get_user_file, save_proto, load_town
from avatar.views import get_avatar_url, get_avatar_filename
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
from pathlib import Path

import google.protobuf
import os

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
        auth_form = AuthCodeForm(initial={"email": request.session["auth_email"]})


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

    # Pre-load forms with user data.
    town_form = UploadTownForm()

    # Pre-load currencies.
    land_data = load_town(request.user)
    currency_form = EditCurrenciesForm(
        initial = {
            "money": land_data.userData.money,
            "donuts": request.user.donuts_balance
        }
    )
 
    if request.method == "POST":

        if "town-form" in request.POST:

            town_form = UploadTownForm(request.POST, request.FILES, prefix="town")

            if town_form.is_valid():

                mayhem_id = request.user.mayhem_id.int
                town_file = get_user_file(mayhem_id, "pb")

                # Validate town file.
                try:
                    land_data = LandData_pb2.LandMessage()
                    land_data.ParseFromString(town_form.cleaned_data["town_file"].read())

                # Reject file
                except google.protobuf.message.DecodeError:
                    messages.error(request, "Invalid town file!", extra_tags="town")

                else:
                    land_data.id = str(request.user.mayhem_id.int)
                    land_data.friendData.name = request.user.username
                    save_proto(town_file, land_data)

                    # Remove user's events file since we are loading a new town.
                    events_file = get_user_file(mayhem_id, "events")

                    if events_file.exists():
                        os.remove(events_file)

                    messages.success(request, "Uploaded town successfuly!", extra_tags="town")

                return HttpResponseRedirect(reverse("dashboard:index"))


        elif "currency-form" in request.POST:

            currency_form = EditCurrenciesForm(request.POST, prefix="currency")

            if currency_form.is_valid():

                currencies = currency_form.cleaned_data

                # Update town file currencies.
                land_data = load_town(request.user)
                land_data.userData.money = currencies["money"]
                save_proto(get_user_file(request.user.mayhem_id.int, "pb"), land_data)

                # Delete all land tokens.
                LandToken.objects.filter(user=request.user).delete()

                # Update donuts.
                request.user.donuts_balance = currencies["donuts"]
                request.user.save(update_fields=["donuts_balance"])

                messages.success(request, "Currencies updated!", extra_tags="currency")
                return HttpResponseRedirect(reverse("dashboard:index"))


    context = {
        "town_form": town_form,
        "town_url": reverse("mh:download_protoland", args=(request.user.mayhem_id.int,)),
        "currency_form": currency_form,
        "avatar_url":  get_avatar_url(request.user.user_id),
        "avatar_exists": get_avatar_filename(request.user.user_id).exists(),
        "username": request.user.username
    }

    return render(request, "dashboard/index.html", context)


@login_required(login_url="dashboard:login")
def profile(request):

    avatar = get_avatar_filename(request.user.user_id)

    if request.method == "POST":
        profile_form = UserProfileForm(request.POST, request.FILES)

        if profile_form.is_valid():

            success = True

            # Update avatar picture if any was uploaded.
            if profile_form.cleaned_data.get("profile_avatar", False):

                avatar_img = profile_form.cleaned_data["profile_avatar"].image

                if avatar_img.format.lower() != "png":
                    messages.error(request, "Image must be png.")
                    success = False

                elif avatar_img.width > 416 or avatar_img.height > 416:
                    messages.error(request, "Image dimensions cannot exceed 416x416 pixels.")
                    success = False

                else:

                    with open(avatar, "wb") as f:
                        for chunk in request.FILES["profile_avatar"].chunks():
                            f.write(chunk)

                    messages.success(request, "Avatar image updated.")


            # Update username if it was edited.
            if profile_form.cleaned_data["profile_username"] not in (".null", request.user.username):
                request.user.username = profile_form.cleaned_data["profile_username"]
                request.user.save(update_fields=["username"])
                messages.success(request, "Username updated.")


            # No errors. Reset the page.
            if success:
                return HttpResponseRedirect(reverse("dashboard:profile"))


    else:
        profile_form = UserProfileForm(initial={"profile_username": request.user.username})


    context = {
        "profile_form": profile_form,
        "avatar_url": get_avatar_url(request.user.user_id),
        "avatar_exists": avatar.exists(),
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
                        "avatar_url": get_avatar_url(user.user_id),
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
                "avatar_url": get_avatar_url(invitation.from_user.user_id),
                "username": invitation.from_user.username,
                "accept_url": reverse("dashboard:friends_accept_request", args=(invitation.from_user.user_id,)),
                "reject_url": reverse("dashboard:friends_cancel_request", args=(invitation.from_user.user_id,))

            } for invitation in request.user.received_invitations.all()
        ],
        key=itemgetter("username")
    )


    sent_requests = sorted(
        [
            {
                "avatar_url": get_avatar_url(invitation.to_user.user_id),
                "username": invitation.to_user.username,
                "cancel_url": reverse("dashboard:friends_cancel_request", args=(invitation.to_user.user_id,))

            } for invitation in request.user.sent_invitations.all()
        ],
        key=itemgetter("username")
    )

    friends = sorted(
        [
            {
                "avatar_url": get_avatar_url(user.user_id),
                "username": user.username,
                "last_active": user.last_authenticated,
                "remove_url": reverse("dashboard:friends_remove", args=(user.user_id,))

            } for user in request.user.friends.all()
        ],
        key=itemgetter("username")
    )



    context = {
        "search_form": search_form,
        "avatar_url":  get_avatar_url(request.user.user_id),
        "avatar_exists": get_avatar_filename(request.user.user_id).exists(),
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
        "avatar_url":  get_avatar_url(request.user.user_id),
        "avatar_exists": get_avatar_filename(request.user.user_id).exists(),
        "username": request.user.username,
        "devices": user_devices
    }

    return render(request, "dashboard/devices.html", context)


@login_required(login_url="dashboard:login")
def remove_device(request, advertising_id):
    get_object_or_404(DeviceToken, advertising_id=advertising_id).delete()
    return HttpResponseRedirect(reverse("dashboard:devices"))
