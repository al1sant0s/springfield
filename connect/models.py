from django.db import models
from django.contrib.auth.models import AbstractBaseUser

import uuid
import secrets

# Create your models here.

class UserId(AbstractBaseUser):
    username = models.CharField(max_length=12)
    email = models.EmailField(unique=True)
    pid_id = models.BigIntegerField(unique=True)
    user_id = models.BigIntegerField(unique=True)
    persona_id = models.BigIntegerField(unique=True)
    telemetry_id = models.BigIntegerField(unique=True)
    mayhem_id = models.UUIDField(default=uuid.uuid4, unique=True)
    date_created = models.DateTimeField("User Date Created")
    session_key = models.CharField(max_length=44, unique=True, default=secrets.token_urlsafe(32))
    last_authenticated = models.DateTimeField("Last Auth Date")
    is_registered = models.BooleanField(default=False)
    land_token = models.UUIDField(default=uuid.uuid4, unique=True)
    donuts_balance = models.PositiveIntegerField(default=50)


class DeviceToken(models.Model):
    user = models.ForeignKey(UserId, on_delete=models.CASCADE)
    advertising_id = models.UUIDField(unique=True)
    code = models.CharField(max_length=64)
    access_token = models.TextField()
    refresh_token = models.TextField()
    session_key = models.CharField(max_length=44, unique=True, default=secrets.token_urlsafe(32))
    timestamp = models.DateTimeField("Token Creation/Update Time")
