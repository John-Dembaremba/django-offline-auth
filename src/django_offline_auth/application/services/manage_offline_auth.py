from django.db import transaction

from django_offline_auth.models import OfflineAuth


def enable_offline_auth(user) -> OfflineAuth:
    """Enable offline authentication for a user."""

    offline_auth, created = OfflineAuth.objects.get_or_create(
        user=user,
    )

    if created:
        return offline_auth

    if not offline_auth.is_enabled:
        offline_auth.is_enabled = True
        offline_auth.credential_version += 1

        offline_auth.save(
            update_fields=[
                "is_enabled",
                "credential_version",
                "updated_at",
            ]
        )

    return offline_auth


def disable_offline_auth(user) -> OfflineAuth:
    """Disable offline authentication for a user."""

    offline_auth, _ = OfflineAuth.objects.get_or_create(
        user=user,
    )

    if offline_auth.is_enabled:
        offline_auth.is_enabled = False

        offline_auth.save(
            update_fields=[
                "is_enabled",
                "updated_at",
            ]
        )

    return offline_auth


@transaction.atomic
def rotate_offline_credentials(user) -> OfflineAuth:
    """Increment the user's offline credential version."""

    offline_auth = OfflineAuth.objects.select_for_update().get(user=user)

    offline_auth.credential_version += 1

    offline_auth.save(
        update_fields=[
            "credential_version",
            "updated_at",
        ]
    )

    return offline_auth
