import secrets
import uuid
from pathlib import Path

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.templatetags.static import static
from django.utils import timezone
from google.protobuf.message import DecodeError
from PIL import Image

from protofiles import LandData_pb2


def avatar_upload_to(instance, filename):
    ext = Path(filename).suffix.lower() or ".png"
    return f"avatars/{instance.user_id}{ext}"


def validate_avatar(file):
    if not file:
        return

    # Skip validation if the file is already committed in storage and not newly uploaded
    if not isinstance(file, UploadedFile) and getattr(file, "_committed", True):
        return

    # 1. Size check
    if file.size > 1048576:
        raise ValidationError("File size exceeds 1MB limit.")

    # 2. Extension check
    if Path(file.name).suffix.lower() not in [".png", ".jpg", ".jpeg"]:
        raise ValidationError("File extension must be .png, .jpg, or .jpeg.")

    # 3. Content checks
    try:
        with Image.open(file) as img:
            if img.format not in ["PNG", "JPEG"]:
                raise ValidationError(
                    "Unsupported image format. Please upload a valid PNG or JPEG."
                )

            if img.width > 416 or img.height > 416:
                raise ValidationError("Image dimensions cannot exceed 416x416 pixels.")

            img.verify()

    except (IOError, SyntaxError):
        raise ValidationError("The uploaded file is not a valid image or is corrupted.")

    finally:
        file.seek(0)


def validate_town(file):
    if not file:
        return

    # Skip validation if the file is already committed in storage and not newly uploaded
    if not isinstance(file, UploadedFile) and getattr(file, "_committed", True):
        return

    # 1. Size check
    if file.size > 5242880:
        raise ValidationError("File size exceeds 5MB limit.")

    # 2. Content checks
    try:
        data = file.read()
        land_data = LandData_pb2.LandMessage()
        land_data.ParseFromString(data)

    except DecodeError:
        try:
            # Fallback for tstole.de backups (starts at 12-byte offset 0x0C)
            land_data.ParseFromString(data[0x0C:])

        except DecodeError:
            raise ValidationError(
                "Invalid town file. The uploaded file is corrupted or not a valid Springfield town file."
            )

    finally:
        file.seek(0)


class UserId(AbstractUser):
    username = models.CharField(
        max_length=16,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z0-9_]{5,16}$",
                message="Username must be between 5 and 16 characters and contain only letters, numbers, and underscores.",
            ),
        ],
    )
    email = models.EmailField(unique=True, null=True)
    is_registered = models.BooleanField(default=False)
    persona_id = models.BigIntegerField(unique=True, null=True, blank=True)
    user_id = models.BigIntegerField(unique=True, null=True, blank=True)
    pid_id = models.BigIntegerField(unique=True, null=True, blank=True)
    telemetry_id = models.BigIntegerField(unique=True, null=True, blank=True)
    mayhem_id = models.UUIDField(default=uuid.uuid4, unique=True)
    session_key = models.CharField(max_length=44, unique=True)
    donuts_balance = models.PositiveIntegerField("Donuts", default=0)
    last_authenticated = models.DateTimeField(default=timezone.now)
    friends = models.ManyToManyField("self", symmetrical=True, blank=True)
    avatar = models.ImageField(
        "Avatar Picture",
        upload_to=avatar_upload_to,
        blank=True,
        validators=[validate_avatar],
    )
    town = models.FileField(
        "Town File", upload_to="towns/", blank=True, validators=[validate_town]
    )
    events = models.BinaryField(default=b"", blank=True)
    friend_data = models.BinaryField(default=b"", blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.username

    def clean(self):
        super().clean()
        if not self.email:
            self.email = None

    @property
    def avatar_url(self):
        try:
            return self.avatar.url
        except (ValueError, AttributeError):
            return static("dashboard/default-avatar.png")

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
                self.username = f"u{self.persona_id}00"

        super().save(*args, **kwargs)


class DeviceToken(models.Model):
    user = models.ForeignKey(
        UserId, on_delete=models.CASCADE, related_name="device_tokens"
    )
    advertising_id = models.UUIDField(primary_key=True)

    # This field exists to circumvent issues with headers with underscores like "access_token".
    # When /connect/tokeninfo is requested we will receive /<uuid:device_id>/connect/tokeninfo
    # and be able to find the DeviceToken. We can also use it in other apps.
    device_id = models.UUIDField(default=uuid.uuid4, unique=True)
    # Fallback for tokeninfo when director is called again.
    device_id_cache = models.UUIDField(unique=True, null=True, blank=True)

    # For mh endpoint POST method identification. Usable in friendData/origin
    current_client_session_id = models.UUIDField(null=True, unique=True, blank=True)
    manufacturer = models.CharField(max_length=64, default="unknown")
    device_model = models.CharField(max_length=64, default="unknown")
    code = models.CharField(max_length=64, unique=True, null=True, blank=True)
    access_token = models.TextField(unique=True, null=True, blank=True)
    refresh_token = models.TextField(unique=True, null=True, blank=True)
    timestamp = models.DateTimeField("Token Creation / Update Time", auto_now=True)
    login_status = models.BooleanField(default=False)

    def __str__(self):
        return self.device_model
