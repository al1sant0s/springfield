from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from django.contrib.auth.views import LoginView, login_required
from django.contrib import messages

from .forms import UploadTownForm, EditCurrenciesForm

from mh.views import get_user_file, save_proto, load_town
from protofiles import LandData_pb2
from pathlib import Path
import google.protobuf

# Create your views here.

def handle_town_file(request, f):

    mayhem_id = request.user.mayhem_id.int
    town_file = get_user_file(mayhem_id, "pb")

    # Validate town file.
    try:
        land_data = LandData_pb2.LandMessage()
        land_data.ParseFromString(f.read())

    # Reject file
    except google.protobuf.message.DecodeError:
        messages.error(request, "Invalid town file!", extra_tags="town")

    else:
        save_proto(town_file, land_data)
        messages.success(request, "Uploaded town successfuly!", extra_tags="town")


def handle_currency(request, currencies):

    # Update town file currencies.
    land_data = load_town(request.user)
    land_data.userData.money = currencies["money"]
    save_proto(get_user_file(request.user.mayhem_id.int, "pb"), land_data)

    # Update donuts.
    request.user.donuts_balance = currencies["donuts"]
    request.user.save()

    messages.success(request, "Currencies updated!", extra_tags="currency")


def check_login(request):

    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("dashboard:index"))

    else:
        return LoginView.as_view(template_name="dashboard/login.html", next_page="dashboard:index")(request)


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
                handle_town_file(request, town_form.cleaned_data["town_file"])
                return HttpResponseRedirect(reverse("dashboard:index"))

        elif "currency-form" in request.POST:

            currency_form = EditCurrenciesForm(request.POST, prefix="currency")

            if currency_form.is_valid():
                handle_currency(request, currency_form.cleaned_data)
                return HttpResponseRedirect(reverse("dashboard:index"))


    return render(request, "dashboard/index.html", {"town_form": town_form, "currency_form": currency_form})
