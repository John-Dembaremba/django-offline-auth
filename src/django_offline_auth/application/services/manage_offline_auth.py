from django_offline_auth.models import OfflineAuth


def enable_offline_auth(user) -> OfflineAuth:
    """Enable offline authentication for a user."""

    offline_auth, _ = OfflineAuth.objects.get_or_create(
        user=user,
    )

    if not offline_auth.is_enabled:
        offline_auth.is_enabled = True
        offline_auth.save(
            update_fields=[
                "is_enabled",
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
