from django.db import models

# Create your models here.

class UserId(models.Model):
    username = models.CharField(max_length = 8)
    email = models.EmailField()
    pid_id = models.IntegerField(default = 0)
    user_id = models.IntegerField(default = 0)
    persona_id = models.IntegerField(default = 0)
    mayhem_id = models.IntegerField(default = 0)




