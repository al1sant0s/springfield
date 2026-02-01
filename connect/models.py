from django.db import models, transaction
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string

import uuid
import secrets

# Create your models here.

class UserId(AbstractUser):
    username = models.CharField(max_length=12, unique=False)
    email = models.EmailField(unique=True)
    is_registered = models.BooleanField(default=False)
    persona_id = models.BigIntegerField(unique=True, blank=True, null=True)
    user_id = models.BigIntegerField(unique=True, blank=True, null=True)
    pid_id = models.BigIntegerField(unique=True, blank=True, null=True)
    telemetry_id = models.BigIntegerField(unique=True, blank=True, null=True)
    mayhem_id = models.UUIDField(default=uuid.uuid4, unique=True)
    session_key = models.CharField(max_length=44, unique=True)
    land_token = models.UUIDField(default=uuid.uuid4, unique=True)
    donuts_balance = models.PositiveIntegerField(default=50)
    last_authenticated = models.DateTimeField(default=timezone.now)
    friends = models.ManyToManyField("self", symmetrical=True)
 
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def reset_password(self, pwd=None):
        if pwd is None:
            self.set_password(secrets.token_urlsafe(32))
        else:
            self.set_password(pwd)


    @transaction.atomic
    def save(self, *args, **kwargs):

        # Fill rest of the fields uppon user creation.
        if self.pk is None:

            try:
                last_user = UserId.objects.latest("persona_id")
            except UserId.DoesNotExist:
                persona_id = 1001000000001
            else:
                persona_id = last_user.persona_id + 1

            # Set each entry in the database accordingly except mayhem_id and land_token which
            # Django will produce values by itself with the default argument specified in models.
            self.persona_id = persona_id
            self.user_id = persona_id + 20000000000
            self.pid_id = self.user_id + 200000
            self.telemetry_id = self.pid_id + 20000000000
            self.session_key = secrets.token_urlsafe(32)

            if self.is_superuser:
                self.is_registered = True

            else:
                self.username = get_random_string(length=12)
                self.email = f"user_{persona_id}@{self.username}.{self.username}" if self.email is None else self.email
                self.reset_password()


        super().save(*args, **kwargs)


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
