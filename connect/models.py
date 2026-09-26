from django.db import models, transaction
from django.forms import ValidationError
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

from springfield.settings import env

from pathlib import Path

import uuid
import secrets

# Create your models here.


class UserId(AbstractUser):
    username = models.CharField(max_length=16, blank=True, unique=True)
    email = models.EmailField(unique=True)
    is_registered = models.BooleanField(default=False)
    persona_id = models.BigIntegerField(unique=True, blank=True, null=True)
    user_id = models.BigIntegerField(unique=True, blank=True, null=True)
    pid_id = models.BigIntegerField(unique=True, blank=True, null=True)
    telemetry_id = models.BigIntegerField(unique=True, blank=True, null=True)
    mayhem_id = models.UUIDField(default=uuid.uuid4, unique=True)
    session_key = models.CharField(max_length=44, unique=True)
    donuts_balance = models.PositiveIntegerField("Donuts", default=50)
    last_authenticated = models.DateTimeField(default=timezone.now)
    friends = models.ManyToManyField("self", symmetrical=True, blank=True)
    avatar = models.ImageField("Avatar Picture", upload_to="avatars/", blank=True)
    town = models.FileField("Town File", upload_to="towns/", blank=True)
    events = models.BinaryField(default=b"", blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.username

    def clean(self):
        super().clean()
        if self.town and self.town.size > 5242880:
            raise ValidationError({"town": "File size exceeds 5MB limit"})
        if self.avatar:
            if self.avatar.size > 1048576:
                raise ValidationError({"avatar": "File size exceeds 1MB limit"})
            if Path(self.avatar.name).suffix.lower() not in [".png", ".jpg", ".jpeg"]:
                raise ValidationError({"avatar": "Image must be either PNG or JPG."})

    @transaction.atomic
    def save(self, *args, **kwargs):
        # Fill rest of the fields upon user creation.
        if self.pk is None:
            last_user = (
                UserId.objects.select_for_update()
                .exclude(
                    persona_id__isnull=True
                )  # Good practice to avoid grabbing a corrupted row
                .order_by("-persona_id")
                .first()
            )

            if last_user is None:
                persona_id = 1001000000001
            else:
                persona_id = last_user.persona_id + 1

            # Set each entry in the database accordingly
            self.persona_id = persona_id
            self.user_id = persona_id + 20000000000
            self.pid_id = self.user_id + 200000
            self.telemetry_id = self.pid_id + 20000000000
            self.session_key = secrets.token_urlsafe(32)
            if self.is_staff:
                self.is_registered = True
            if not self.password:
                self.set_unusable_password()
            if not self.username:
                self.username = f"u{self.persona_id}{secrets.token_hex(1)}"
            if not self.email:
                self.email = f"{self.username}@user.com"

        super().save(*args, **kwargs)


class DeviceToken(models.Model):
    user = models.ForeignKey(
        UserId, on_delete=models.CASCADE, related_name="device_tokens"
    )
    advertising_id = models.UUIDField(primary_key=True)

    # This field exists to circuvent issues with headers with underscores like "access_token".
    # When /connect/tokeninfo is requested we will receive /<uuid:device_id>/connect/tokeninfo
    # and be able to find the DeviceToken. We can also use it in other apps.
    device_id = models.UUIDField(default=uuid.uuid4, unique=True)
    # Fallback for tokeninfo when director is called again.
    device_id_cache = models.UUIDField(unique=True, null=True, blank=True)

    # For mh endpoint POST method identification. Usable in friendData/origin
    current_client_session_id = models.UUIDField(null=True, blank=True)
    manufacturer = models.CharField(max_length=64, default="unknown")
    device_model = models.CharField(max_length=64, default="unknown")
    code = models.CharField(max_length=64, blank=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    timestamp = models.DateTimeField("Token Creation / Update Time", auto_now=True)
    login_status = models.BooleanField(default=False)

    def __str__(self):
        return self.device_model
