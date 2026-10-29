from django.contrib.auth.hashers import identify_hasher

from django_offline_auth.exceptions import CredentialGenerationError
from django_offline_auth.protocol.constants import (
    SUPPORTED_PASSWORD_ALGORITHMS,
)


class DjangoPasswordCredentialProvider:
    """Provides a supported Django password verifier."""

    def get_verifier(self, user) -> str:
        if not user.has_usable_password():
            raise CredentialGenerationError("User does not have a usable password.")

        verifier = getattr(user, "password", None)

        if not verifier:
            raise CredentialGenerationError("User does not have a password verifier.")

        try:
            hasher = identify_hasher(verifier)
        except ValueError as exc:
            raise CredentialGenerationError(
                "User password verifier is invalid."
            ) from exc

        if hasher.algorithm not in SUPPORTED_PASSWORD_ALGORITHMS:
            raise CredentialGenerationError(
                f"Unsupported password algorithm: {hasher.algorithm}"
            )

        return verifier
