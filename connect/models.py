from django.db import models

import uuid

# Create your models here.

class UserId(models.Model):
    username = models.CharField(max_length=12)
    email = models.EmailField(unique=True)
    pid_id = models.BigIntegerField(unique=True)
    user_id = models.BigIntegerField(unique=True)
    persona_id = models.BigIntegerField(unique=True)
    telemetry_id = models.BigIntegerField(unique=True)
    mayhem_id = models.UUIDField(default=uuid.uuid4, unique=True)
    date_created = models.DateTimeField("User Date Created")
    last_authenticated = models.DateTimeField("Last Auth Date")
    is_registered = models.BooleanField(default=False)


class DeviceToken(models.Model):
    user = models.ForeignKey(UserId, on_delete=models.CASCADE)
    advertising_id = models.UUIDField(unique=True)
    code = models.CharField(max_length=64)
    access_token = models.TextField()
    refresh_token = models.TextField()
    timestamp = models.FloatField("Token Creation/Update Time")
