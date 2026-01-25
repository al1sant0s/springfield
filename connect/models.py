from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

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
    session_key = models.CharField(max_length=44, unique=True)
    land_token = models.UUIDField(default=uuid.uuid4, unique=True)
    donuts_balance = models.PositiveIntegerField(default=50)
    date_created = models.DateTimeField("User Date Created", default=timezone.now)
    last_authenticated = models.DateTimeField("Last Auth Date", default=timezone.now)
    friends = models.ManyToManyField("self")


    def reset_password(self, pwd = None):
        # If password is not specified, generate a random one.
        if pwd is None:
            self.set_password(secrets.token_urlsafe(32))

        else:
            self.set_password(pwd)


class DeviceToken(models.Model):
    user = models.ForeignKey(UserId, on_delete=models.CASCADE)
    advertising_id = models.UUIDField(primary_key=True)
    # This field exists to circuvent issues with headers with underscores like "access_token".
    # When /connect/tokeninfo is requested we will receive /<uuid:device_id>/connect/tokeninfo
    # and be able to find the DeviceToken. We can also use it in other apps.
    device_id = models.UUIDField(unique=True)
    device_id_cache = models.UUIDField(unique=True) # Fallback for tokeninfo when director is called again.
    # For mh endpoint POST method identification. Usable in friendData/origin
    current_client_session_id = models.UUIDField(null=True, blank=True)
    code = models.CharField(max_length=64)
    access_token = models.TextField()
    refresh_token = models.TextField()
    session_key = models.CharField(max_length=44, unique=True)
    timestamp = models.DateTimeField("Token Creation/Update Time")
    login_status = models.BooleanField(default=False)
