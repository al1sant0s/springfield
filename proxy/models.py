from django.db import models

from connect.models import UserId, DeviceToken

import datetime
import random

# Create your models here.

class ProgRegCode(models.Model):
    email = models.EmailField(primary_key=True)
    code = models.PositiveIntegerField()
    expiry_on = models.DateField()
    token = models.ForeignKey(DeviceToken, on_delete=models.CASCADE)
