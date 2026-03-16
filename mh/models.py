from django.db import models
from django.utils import timezone

from connect.models import UserId

import uuid
import datetime

# Create your models here.

class LandToken(models.Model):
    user = models.OneToOneField(UserId, on_delete=models.CASCADE)
    land_token = models.UUIDField(default=uuid.uuid4, unique=True)
    retrieved = models.BooleanField(default=False)
    authorized = models.BooleanField(default=False)
    remove = models.BooleanField(default=False)
