from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth.views import LoginView, login_required
from django.contrib.auth.models import BaseUserManager

from connect.models import UserId, DeviceToken
from proxy.models import ProgRegCode
from proxy.views import get_auth_code
from mh.views import get_user_file, save_proto, load_town
from avatar.views import get_avatar_url

from .forms import UploadTownForm
from .forms import EditCurrenciesForm
from .forms import RequestUserForm
from .forms import AuthCodeForm
from .forms import ResetPasswordForm
from .forms import UserProfileForm

from protofiles import LandData_pb2
from pathlib import Path

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
                get_auth_code(email, None)
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
                return HttpResponseRedirect(reverse("dashboard:register"))

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
                get_auth_code(email, None)
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
                user.save()

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
                    save_proto(town_file, land_data)
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

                # Update donuts.
                request.user.donuts_balance = currencies["donuts"]
                request.user.save()

                messages.success(request, "Currencies updated!", extra_tags="currency")
                return HttpResponseRedirect(reverse("dashboard:index"))


    return render(request, "dashboard/index.html", {"town_form": town_form, "currency_form": currency_form})


@login_required(login_url="dashboard:login")
def user_profile(request):

    avatar_url = f"{get_avatar_url()}/{request.user.user_id}.png"

    if request.method == "POST":
        profile_form = UserProfileForm(request.POST, request.FILES)

        if profile_form.is_valid():

            if profile_form.cleaned_data.get("profile_avatar", False):

                avatar_img = profile_form.cleaned_data["profile_avatar"].image

                if avatar_img.format.lower() != "png":
                    messages.error(request, "Image must be png.")

                elif avatar_img.width > 416 or avatar_img.height > 416:
                    messages.error(request, "Image dimensions cannot exceed 416x416 pixels.")

                else:

                    with open(Path(cache.get("avatar_dir"), f"{request.user.user_id}.png"), "wb") as f:
                        for chunk in request.FILES["profile_avatar"].chunks():
                            f.write(chunk)

                    messages.success(request, "Avatar image updated.")



            if profile_form.cleaned_data["profile_username"] not in (".null", request.user.username):
                request.user.username = profile_form.cleaned_data["profile_username"]
                request.user.save()
                messages.success(request, "Username updated.")


    else:
        profile_form = UserProfileForm(initial={"profile_username": request.user.username})

    return render(request, "dashboard/user-profile.html", {"profile_form": profile_form, "avatar_url": avatar_url})
