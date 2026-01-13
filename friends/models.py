from django.db import models

from connect.models import UserId

# Create your models here.

class FriendInvitation(models.Model):
    from_user = models.ForeignKey(UserId, on_delete=models.CASCADE, related_name="sent_invitations")
    to_user = models.ForeignKey(UserId, on_delete=models.CASCADE, related_name="received_invitations")
    invitation_date = models.DateTimeField()
