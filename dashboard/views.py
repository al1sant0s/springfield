from django.contrib.auth.views import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import generic

from .forms import LoginForm

# Create your views here.

@login_required(login_url="dashboard:login")
def index(request):
    return HttpResponse("<h1>Congratulations!</h1>")
