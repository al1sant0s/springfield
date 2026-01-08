from django.contrib import admin

from .models import UserId, DeviceToken

# Register your models here.

admin.site.register(UserId)
admin.site.register(DeviceToken)

