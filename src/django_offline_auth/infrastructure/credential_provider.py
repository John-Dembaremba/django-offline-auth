from django.contrib.auth.hashers import identify_hasher

from django_offline_auth.exceptions import CredentialGenerationError


class DjangoPasswordCredentialProvider:
    """Provides a supported Django password verifier. By default Django uses 'pbkdf2_sha256', which this version supports so far"""

    def __init__(self):
        self.supported_algorithms = {
            "pbkdf2_sha256",
        }

    def get_verifier(self, user) -> str:
        verifier = getattr(user, "password", None)

        if not verifier:
            raise CredentialGenerationError("User does not have a password verifier.")

        try:
            hasher = identify_hasher(verifier)
        except ValueError as exc:
            raise CredentialGenerationError(
                "User password verifier is invalid."
            ) from exc

        if hasher.algorithm not in self.supported_algorithms:
            raise CredentialGenerationError(
                f"Unsupported password algorithm: {hasher.algorithm}"
            )

        return verifier
