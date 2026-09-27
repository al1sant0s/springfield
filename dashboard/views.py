from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, login_required
from django.contrib.auth.models import BaseUserManager
from django.db.models.functions import Lower

from connect.models import UserId, DeviceToken
from mh.models import LandToken
from proxy.views import request_auth_code, validate_auth_code, search_friends
from mh.views import save_town, load_town
from friends.views import (
    send_friend_request,
    cancel_friend_request,
    accept_friend_request,
    remove_friend,
)

from .forms import UploadTownForm
from .forms import EditCurrenciesForm
from .forms import RequestUserForm
from .forms import AuthCodeForm
from .forms import ResetPasswordForm
from .forms import UserProfileForm
from .forms import SearchUserForm
from .forms import DeleteUserForm

from protofiles import LandData_pb2

import requests

# Create your views here.

def login(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("dashboard:index"))

    else:
        if request.method == "GET":
            request.session["next"] = request.GET.get("next", "dashboard:index")

        return LoginView.as_view(
            template_name="dashboard/login.html",
            next_page=request.session.get("next", "dashboard:index"),
        )(request)


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
                request_auth_code(email)
                request.session["auth_email"] = email
                return HttpResponseRedirect(reverse("dashboard:auth"))

    return render(request, "dashboard/register.html", {"register_form": register_form})


def forgot_password(request):
    forgot_form = RequestUserForm()

    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("dashboard:index"))

    elif request.method == "POST":
        forgot_form = RequestUserForm(request.POST)

        if forgot_form.is_valid():
            email = BaseUserManager.normalize_email(forgot_form.cleaned_data["email"])
            user = UserId.objects.filter(email__iexact=email).first()

            # Verify if account does not exist.
            if not user:
                messages.error(request, "No account was found with this email.")

            elif user.is_superuser:
                messages.error(
                    request,
                    "You are not allowed to change your password in here. Contact the server administrator!",
                )

            else:
                request_auth_code(email)
                request.session["auth_email"] = email
                return HttpResponseRedirect(reverse("dashboard:auth"))

    return render(
        request, "dashboard/forgot-password.html", {"forgot_form": forgot_form}
    )


def auth(request):
    if "auth_email" not in request.session:
        return HttpResponseRedirect(reverse("dashboard:login"))

    elif request.method == "POST":
        auth_form = AuthCodeForm(request.POST)
        if auth_form.is_valid():
            email = request.session["auth_email"]
            code = auth_form.cleaned_data["code"]
            status = validate_auth_code(email, code)
            if status:
                user, _ = UserId.objects.get_or_create(
                    email=request.session["auth_email"], is_registered=True
                )
                request.session["auth_username"] = user.username
                return HttpResponseRedirect(reverse("dashboard:reset_password"))

            elif status is None:
                return HttpResponseRedirect(reverse("dashboard:login"))

            else:
                messages.error(request, "Wrong code.")

    else:
        auth_form = AuthCodeForm()

    return render(
        request,
        "dashboard/auth.html",
        {"auth_form": auth_form, "email": request.session["auth_email"]},
    )


def reset_password(request):
    if "auth_email" not in request.session or "auth_username" not in request.session:
        return HttpResponseRedirect(reverse("dashboard:login"))

    elif request.method == "POST":
        password_form = ResetPasswordForm(request.POST)

        if password_form.is_valid():
            user = get_object_or_404(UserId, email=request.session["auth_email"])
            new_username = password_form.cleaned_data["username"]

            # Only check if user actually changed their username
            if new_username != user.username:
                if UserId.objects.filter(username__iexact=new_username).exists():
                    messages.error(request, "This username is already taken.")
                    return render(
                        request,
                        "dashboard/reset-password.html",
                        {"password_form": password_form},
                    )
                user.username = new_username

            user.set_password(password_form.cleaned_data["password"])
            user.save(update_fields=["username", "password"])

            # User will have to request a new auth code to be able to revisit the reset password view.
            request.session.pop("auth_email", None)
            request.session.pop("auth_username", None)
            return HttpResponseRedirect(reverse("dashboard:login"))

    else:
        password_form = ResetPasswordForm(
            initial={"username": request.session["auth_username"]}
        )

    return render(
        request, "dashboard/reset-password.html", {"password_form": password_form}
    )


@login_required(login_url="dashboard:login")
def index(request):
    if request.method == "POST":
        if "town-form" in request.POST:
            town_form = UploadTownForm(
                request.POST, request.FILES, instance=request.user
            )
            if town_form.is_valid():
                town_form.save()
                LandToken.objects.filter(user=request.user).update(
                    authorized=False, remove=True
                )
                messages.success(
                    request, "Uploaded town successfully!", extra_tags="town"
                )
                return HttpResponseRedirect(reverse("dashboard:index"))

            # Lazy load currency form to avoid unnecessary database queries if the town form is valid.
            land_data = LandData_pb2.LandMessage()
            land_data.ParseFromString(load_town(request.user))
            currency_form = EditCurrenciesForm(
                instance=request.user, initial={"money": land_data.userData.money}
            )

        elif "currency-form" in request.POST:
            land_data = LandData_pb2.LandMessage()
            land_data.ParseFromString(load_town(request.user))
            currency_form = EditCurrenciesForm(
                request.POST,
                instance=request.user,
                initial={"money": land_data.userData.money},
            )
            if currency_form.is_valid():
                if currency_form.has_changed():
                    if "money" in currency_form.changed_data:
                        land_data.userData.money = currency_form.cleaned_data["money"]
                        save_town(request.user, land_data.SerializeToString())

                    if "donuts_balance" in currency_form.changed_data:
                        currency_form.save()

                    LandToken.objects.filter(user=request.user).update(
                        authorized=False, remove=True
                    )

                    messages.success(
                        request, "Currencies updated!", extra_tags="currency"
                    )

                else:
                    messages.info(
                        request, "No changes were made.", extra_tags="currency"
                    )

                return HttpResponseRedirect(reverse("dashboard:index"))

            town_form = UploadTownForm()

        else:
            return HttpResponseRedirect(reverse("dashboard:index"))

    else:
        town_form = UploadTownForm()
        land_data = LandData_pb2.LandMessage()
        land_data.ParseFromString(load_town(request.user))
        currency_form = EditCurrenciesForm(
            instance=request.user, initial={"money": land_data.userData.money}
        )

    return render(
        request,
        "dashboard/index.html",
        {"town_form": town_form, "currency_form": currency_form},
    )


@login_required(login_url="dashboard:login")
def profile(request):
    if request.method == "POST":
        profile_form = UserProfileForm(
            request.POST, request.FILES, instance=request.user
        )
        if profile_form.is_valid():
            if profile_form.has_changed():
                if "avatar" in profile_form.changed_data:
                    messages.success(request, "Avatar image updated.")

                if "username" in profile_form.changed_data:
                    messages.success(request, "Username updated.")

                profile_form.save()
            else:
                messages.info(request, "No changes were made.")

            return HttpResponseRedirect(reverse("dashboard:profile"))

    else:
        profile_form = UserProfileForm(instance=request.user)

    return render(request, "dashboard/profile.html", {"profile_form": profile_form})

@login_required(login_url="dashboard:login")
def friends(request):
    if request.method == "POST":
        search_form = SearchUserForm(request.POST)
        search_matches = list()

        if search_form.is_valid():
            username = search_form.cleaned_data["search_text"]

            # Sort by alphabetical order.
            search_matches = [
                user for user in search_friends(request.user, username)[:100]
            ]

    else:
        search_form = SearchUserForm()
        search_matches = list()

    # Get pending requests.
    received_requests = request.user.received_invitations.select_related(
        "from_user"
    ).order_by("-invitation_date")

    sent_requests = request.user.sent_invitations.select_related("to_user").order_by(
        "-invitation_date"
    )

    friends = request.user.friends.order_by(Lower("username"))

    context = {
        "search_form": search_form,
        "search_matches": search_matches,
        "received_requests": received_requests,
        "sent_requests": sent_requests,
        "friends": friends,
    }

    return render(request, "dashboard/friends.html", context)


@login_required(login_url="dashboard:login")
def friends_send_request(request, to_user_id):
    from_user = request.user
    to_user = get_object_or_404(UserId, user_id=to_user_id)
    return send_friend_request(
        from_user, to_user, HttpResponseRedirect(reverse("dashboard:friends"))
    )


@login_required(login_url="dashboard:login")
def friends_cancel_request(request, to_user_id):
    from_user = request.user
    to_user = get_object_or_404(UserId, user_id=to_user_id)
    return cancel_friend_request(
        from_user, to_user, HttpResponseRedirect(reverse("dashboard:friends"))
    )


@login_required(login_url="dashboard:login")
def friends_accept_request(request, from_user_id):
    from_user = get_object_or_404(UserId, user_id=from_user_id)
    to_user = request.user
    return accept_friend_request(
        from_user, to_user, HttpResponseRedirect(reverse("dashboard:friends"))
    )


@login_required(login_url="dashboard:login")
def friends_reject_request(request, from_user_id):
    from_user = get_object_or_404(UserId, user_id=from_user_id)
    to_user = request.user
    return cancel_friend_request(
        from_user, to_user, HttpResponseRedirect(reverse("dashboard:friends"))
    )


@login_required(login_url="dashboard:login")
def friends_remove(request, to_user_id):
    from_user = request.user
    to_user = get_object_or_404(UserId, user_id=to_user_id)
    return remove_friend(
        from_user, to_user, HttpResponseRedirect(reverse("dashboard:friends"))
    )


@login_required(login_url="dashboard:login")
def devices(request):
    user_devices = [
        {
            "manufacturer": token.manufacturer,
            "model": token.device_model,
            "last_active": token.timestamp,
            "remove_url": reverse(
                "dashboard:remove_device", args=(token.advertising_id,)
            ),
        }
        for token in request.user.device_tokens.all()
    ]

    return render(request, "dashboard/devices.html", {"devices": user_devices})


@login_required(login_url="dashboard:login")
def remove_device(request, advertising_id):
    get_object_or_404(
        DeviceToken, user=request.user, advertising_id=advertising_id
    ).delete()
    return HttpResponseRedirect(reverse("dashboard:devices"))


@login_required(login_url="dashboard:login")
def delete_account(request):
    if request.method == "POST":
        delete_user_form = DeleteUserForm(request.POST)

        if delete_user_form.is_valid():
            status = validate_auth_code(
                request.user.email, delete_user_form.cleaned_data["code"]
            )
            if status:

                # Send email notifying about account termination and data removal.
                apikey = cache.get("tsto_api_key")
                response = requests.post("https://tsto.app/api/account/wipeNotice",
                    params={"apikey": apikey},
                    data={
                        "emailAddress": request.user.email,
                        "wipedBy": request.user.username,
                        "source": cache.get("tsto_api_team_name", default="TSTO API"),
                        "deletedItems": [
                            "Device data.",
                            "Login tokens.",
                            "Profile picture.",
                            "Username.",
                            "Email address.",
                            "Advertisting ID.",
                        ],
                    }
                )

                # Delete only if the API confirms the user was notified via email.
                # If the API is not configured, ignore the condition and delete the user anyways.
                if not apikey or (response.status_code == 200 and response.json().get("success")):
                    request.user.town.delete()
                    request.user.avatar.delete()
                    request.user.delete()
                    logout(request)
                    return HttpResponseRedirect(reverse("dashboard:login"))

                messages.error(request, "A notification email could not be delivered. Try again!")

            elif status is None:
                return HttpResponseRedirect(reverse("dashboard:profile"))

            else:
                messages.error(request, "Wrong code.")

    else:
        request_auth_code(request.user.email)
        delete_user_form = DeleteUserForm()

    context = {
        "delete_user_form": delete_user_form,
    }

    return render(request, "dashboard/delete-account.html", context)
