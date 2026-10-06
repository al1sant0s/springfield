from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from mh.models import LandToken

from .models import DeviceToken, UserId


class LandTokenInLine(admin.TabularInline):
    model = LandToken
    extra = 0
    fields = ["land_token", "retrieved", "authorized", "remove"]
    readonly_fields = ["land_token"]

    def has_add_permission(self, request, obj):
        return False


class DeviceTokenInLine(admin.TabularInline):
    model = DeviceToken
    extra = 0
    fields = [
        "manufacturer",
        "device_model",
        "login_status",
    ]

    def has_add_permission(self, request, obj):
        return False


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = [
        "advertising_id",
        "user",
        "device_model",
        "login_status",
        "timestamp",
    ]
    list_filter = ["login_status", "device_model"]
    search_fields = ["advertising_id", "user__email", "user__username"]
    readonly_fields = [
        "advertising_id",
        "device_id",
        "device_id_cache",
        "current_client_session_id",
        "code",
        "access_token",
        "refresh_token",
        "timestamp",
    ]
    fieldsets = [
        (
            "Device Details",
            {"fields": ("advertising_id", "timestamp", "device_model", "login_status")},
        ),
        (
            "Game Identifiers",
            {
                "fields": (
                    "device_id",
                    "device_id_cache",
                    "current_client_session_id",
                    "code",
                    "access_token",
                    "refresh_token",
                )
            },
        ),
    ]

    def has_add_permission(self, request):
        return False


@admin.register(UserId)
class UserIdAdmin(UserAdmin):
    list_display = ["email", "username", "is_registered", "last_authenticated"]
    list_filter = ["is_superuser", "is_registered", "is_active"]
    search_fields = ["advertising_id", "user__email", "user__username"]
    ordering = ["-persona_id"]
    filter_horizontal = ("friends",)
    readonly_fields = (
        "email",
        "persona_id",
        "user_id",
        "pid_id",
        "telemetry_id",
        "mayhem_id",
        "session_key",
        "last_login",
        "last_authenticated",
    )

    fieldsets = (
        (
            "Account Credentials",
            {
                "fields": ("username", "email", "password"),
            },
        ),
        (
            "Game Identifiers",
            {
                "fields": (
                    "persona_id",
                    "user_id",
                    "pid_id",
                    "telemetry_id",
                    "mayhem_id",
                    "session_key",
                ),
            },
        ),
        (
            "Status",
            {
                "fields": ("is_registered", "is_active", "is_staff", "is_superuser"),
            },
        ),
        ("Activity", {"fields": ("last_authenticated", "last_login")}),
        (
            "Game Data",
            {
                "fields": (
                    "donuts_balance",
                    "avatar",
                    "town",
                    "friends",
                ),
            },
        ),
    )
    inlines = [DeviceTokenInLine, LandTokenInLine]
