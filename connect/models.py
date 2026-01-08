import uuid
from django.db import models

# Create your models here.

class UserId(models.Model):
    username = models.CharField(max_length=8)
    email = models.EmailField(unique=True)
    pid_id = models.IntegerField(unique=True)
    user_id = models.IntegerField(unique=True)
    persona_id = models.BigIntegerField(unique=True)
    mayhem_id = models.IntegerField(unique=True)


    # Generate all ids.
    def __init__(self):
        try:
            last_user = UserId.objects.latest('id')
        except UserId.DoesNotExist:
            self.persona_id = 1001000000000
        else:
            self.persona_id = last_user.persona_id + 1


        self.user_id = self.persona_id + 20000000000
        self.pid_id = self.user_id + 200000
        self.mayhem_id = uuid.uuid4().int


class DeviceToken(models.Model):
    user = models.ForeignKey(UserId, on_delete=models.CASCADE)
    advertisingId = models.UUIDField(unique=True)
    access_token_base64 = models.TextField()
    refresh_token_base64 = models.TextField()
