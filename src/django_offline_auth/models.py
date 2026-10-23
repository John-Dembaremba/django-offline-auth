from django.conf import settings
from django.db import models


class OfflineAuth(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="offline_auth",
    )

    is_enabled = models.BooleanField(
        default=True,
    )

    credential_version = models.PositiveIntegerField(
        default=1,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Offline authentication"
        verbose_name_plural = "Offline authentication"

    def __str__(self) -> str:
        return f"OfflineAuth<{self.user}>"
