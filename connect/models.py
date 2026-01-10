from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password

import uuid
import secrets

# Create your models here.

class UserId(AbstractBaseUser):
    USERNAME_FIELD = "username"
    username = models.CharField(max_length=12)
    email = models.EmailField(unique=True)
    is_registered = models.BooleanField(default=False)
    pid_id = models.BigIntegerField(unique=True)
    user_id = models.BigIntegerField(unique=True)
    persona_id = models.BigIntegerField(unique=True)
    telemetry_id = models.BigIntegerField(unique=True)
    mayhem_id = models.UUIDField(default=uuid.uuid4, unique=True)
    session_key = models.CharField(max_length=44, unique=True, default=secrets.token_urlsafe(32))
    land_token = models.UUIDField(default=uuid.uuid4, unique=True)
    donuts_balance = models.PositiveIntegerField(default=50)
    date_created = models.DateTimeField("User Date Created")
    last_authenticated = models.DateTimeField("Last Auth Date")


    def normalize_email(self):
        self.email = BaseUserManager.normalize_email(self.email)


    def reset_password(self, pwd = None):
        # If password is not specified, generate a random one.
        if pwd is None:
            self.set_password(secrets.token_urlsafe(32))

        else:
            self.set_password(pwd)


class DeviceToken(models.Model):
    user = models.ForeignKey(UserId, on_delete=models.CASCADE)
    advertising_id = models.UUIDField(primary_key=True)
    code = models.CharField(max_length=64)
    access_token = models.TextField()
    refresh_token = models.TextField()
    session_key = models.CharField(max_length=44, unique=True, default=secrets.token_urlsafe(32))
    timestamp = models.DateTimeField("Token Creation/Update Time")
