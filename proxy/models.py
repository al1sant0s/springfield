from django.db import models

from connect.models import DeviceToken

# Create your models here.

class ProgRegCode(models.Model):
    email = models.EmailField(primary_key=True)
    code = models.CharField(max_length=6)
    expiry_on = models.DateTimeField()
    token = models.ForeignKey(DeviceToken, on_delete=models.CASCADE)
