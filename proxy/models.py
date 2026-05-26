from django.db import models

# Create your models here.

class ProgRegCode(models.Model):
    email = models.EmailField(primary_key=True)
    code = models.CharField(max_length=6)
    expiry_on = models.DateTimeField()
