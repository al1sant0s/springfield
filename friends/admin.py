from django.contrib import admin

from .models import FriendInvitation

# Register your models here.

class FriendInvitationAdmin(admin.ModelAdmin):
    search_fields = ["from_user__username", "to_user__username"]
    readonly_fields = ["invitation_date"]

admin.site.register(FriendInvitation, FriendInvitationAdmin)
