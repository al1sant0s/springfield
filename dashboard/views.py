from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from django.contrib.auth.views import LoginView, login_required
from django.contrib import messages

from .forms import UploadTownForm, EditCurrenciesForm

from mh.views import get_towns_dir, save_proto, starting_town
from protofiles import LandData_pb2
from pathlib import Path
import google.protobuf

# Create your views here.

def handle_town_file(request, f):

    mayhem_id = request.user.mayhem_id.int
    town_file = Path(get_towns_dir(), f"{mayhem_id}/{mayhem_id}.pb")
    town_file.parent.mkdir(parents=True, exist_ok=True)

    # Validate town file.
    try:
        land_data = LandData_pb2.LandMessage()
        land_data.ParseFromString(f.read())

    # Reject file
    except google.protobuf.message.DecodeError:
        messages.error(request, "Invalid town file!")

    else:
        save_proto(town_file, land_data)
        messages.success(request, "Uploaded town successfuly!")


def check_login(request):

    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("dashboard:index"))

    else:
        return LoginView.as_view(template_name="dashboard/login.html", next_page="dashboard:index")(request)


@login_required(login_url="dashboard:login")
def index(request):
 
    if request.method == "POST":
        town_form = UploadTownForm(request.POST, request.FILES, prefix="town")
        currency_form = EditCurrenciesForm(request.POST, prefix="currency_form")

        # Town file.
        if town_form.is_valid():
            handle_town_file(request, town_form.cleaned_data["town_file"])

    else:
        town_form = UploadTownForm()
        currency_form = EditCurrenciesForm()


    return render(request, "dashboard/index.html", {"town_form": town_form, "currency_form": currency_form})
