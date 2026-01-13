from django.db import models

from connect.models import DeviceToken

# Create your models here.

class ProgRegCode(models.Model):
    email = models.EmailField(primary_key=True)
    code = models.PositiveIntegerField()
    expiry_on = models.DateTimeField()
    token = models.ForeignKey(DeviceToken, on_delete=models.CASCADE)
