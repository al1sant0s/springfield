from django.db import models
from django.db.models.functions import Greatest, Least
from connect.models import UserId


# Create your models here.

class FriendInvitation(models.Model):
    from_user = models.ForeignKey(UserId, on_delete=models.CASCADE, related_name="sent_invitations")
    to_user = models.ForeignKey(UserId, on_delete=models.CASCADE, related_name="received_invitations")
    invitation_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Least("from_user", "to_user"),
                Greatest("from_user", "to_user"),
                name="unique_bidirectional_relationship",
            ),
            models.CheckConstraint(
                condition=~models.Q(from_user=models.F("to_user")),
                name="cannot_befriend_yourself"
            )
        ]

    def __str__(self):
        return f"{self.from_user} >>> {self.to_user}"
