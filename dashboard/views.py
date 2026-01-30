from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from django.contrib.auth.views import LoginView, login_required

# Create your views here.

def check_login(request):

    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("dashboard:index"))

    else:
        return LoginView.as_view(template_name="dashboard/login.html", next_page="dashboard:index")(request)


@login_required(login_url="dashboard:login")
def index(request):
    return HttpResponse("<h1>Congratulations!</h1>")
