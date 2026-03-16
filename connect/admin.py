from django.contrib import admin

from .models import UserId, DeviceToken
from mh.models import LandToken

# Register your models here.

class DeviceTokenInLine(admin.TabularInline):
    model = DeviceToken
    extra = 0
    fieldsets = [
        (
            "Identity",
            {
                "fields":
                    [
                        "manufacturer",
                        "device_model",
                    ]
            }
        ),
        (
            "Activity",
            {
                "fields":
                    [
                        "login_status",
                        "timestamp",
                    ]
            }
        ),
    ]


class LandTokenInLine(admin.StackedInline):
    model = LandToken
    extra = 0


class UserIdAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "last_login"]
    list_filter = ["is_superuser", "is_registered"]
    fieldsets = [
        (
            "Identity",
            {
                "fields":
                    [
                        "username",
                        "email",
                        "persona_id",
                        "user_id",
                        "pid_id",
                        "telemetry_id",
                    ]
            }
        ),
        (
            "Activity",
            {
                "fields":
                    [
                        "is_registered",
                        "last_login",
                        "last_authenticated",
                    ]
            }
        ),
    ]
    inlines = [LandTokenInLine, DeviceTokenInLine]


admin.site.register(UserId, UserIdAdmin)
admin.site.register(DeviceToken)
