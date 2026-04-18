from django.db import models

from connect.models import UserId

# Create your models here.

class FriendInvitation(models.Model):
    from_user = models.ForeignKey(UserId, on_delete=models.CASCADE, related_name="sent_invitations")
    to_user = models.ForeignKey(UserId, on_delete=models.CASCADE, related_name="received_invitations")
    invitation_date = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"], 
                name="unique_invitation_direction"
            ),
            models.UniqueConstraint(
                fields=["to_user", "from_user"],
                name="unique_reverse_invitation"
            ),
            models.CheckConstraint(
                condition=~models.Q(from_user=models.F("to_user")),
                name="cannot_befriend_yourself"
            )
        ]
