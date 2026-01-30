from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from django.contrib.auth.views import LoginView, login_required
from django.contrib import messages

from .forms import DashForm

from mh.views import get_towns_dir, save_proto, starting_town
from protofiles import LandData_pb2
from pathlib import Path
import google.protobuf

# Create your views here.

def handle_town_file(user, f):

    mayhem_id = user.mayhem_id.int
    town_file = Path(get_towns_dir(), f"{mayhem_id}/{mayhem_id}.pb")
    town_file.parent.mkdir(parents=True, exist_ok=True)

    # Validate town file.
    try:
        land_data = LandData_pb2.LandMessage()
        land_data.ParseFromString(f.read())

    # Reject file
    except google.protobuf.message.DecodeError:
        return False

    else:
        save_proto(town_file, land_data)
        return True


def check_login(request):

    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("dashboard:index"))

    else:
        return LoginView.as_view(template_name="dashboard/login.html", next_page="dashboard:index")(request)


@login_required(login_url="dashboard:login")
def index(request):
 
    if request.method == "POST":
        form = DashForm(request.POST, request.FILES)

        if form.is_valid():

            if handle_town_file(request.user, request.FILES["town_file"]):
                messages.success(request, "Uploaded town successfuly!")

            else:
                messages.error(request, "Invalid town file!")


            return HttpResponseRedirect(reverse("dashboard:index"))

    else:
        form = DashForm()


    return render(request, "dashboard/index.html", {"form": form})
