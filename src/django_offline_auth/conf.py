from datetime import timedelta

from django.conf import settings

DEFAULT_CREDENTIAL_TTL = timedelta(hours=24)
DEFAULT_MIN_RSA_KEY_SIZE = 2048


def get_credential_ttl() -> timedelta:
    """Return the configured offline credential lifetime."""
    seconds = getattr(
        settings,
        "DJANGO_OFFLINE_AUTH_CREDENTIAL_TTL_SECONDS",
        int(DEFAULT_CREDENTIAL_TTL.total_seconds()),
    )

    if not isinstance(seconds, int):
        raise TypeError(
            "DJANGO_OFFLINE_AUTH_CREDENTIAL_TTL_SECONDS must be an integer."
        )

    if seconds <= 0:
        raise ValueError(
            "DJANGO_OFFLINE_AUTH_CREDENTIAL_TTL_SECONDS must be greater than 0."
        )

    return timedelta(seconds=seconds)


def get_min_rsa_key_size() -> int:
    """Return the minimum accepted RSA public key size."""
    key_size = getattr(
        settings,
        "DJANGO_OFFLINE_AUTH_MIN_RSA_KEY_SIZE",
        DEFAULT_MIN_RSA_KEY_SIZE,
    )

    if not isinstance(key_size, int):
        raise TypeError("DJANGO_OFFLINE_AUTH_MIN_RSA_KEY_SIZE must be an integer.")

    if key_size < 2048:
        raise ValueError("DJANGO_OFFLINE_AUTH_MIN_RSA_KEY_SIZE must be at least 2048.")

    return key_size
