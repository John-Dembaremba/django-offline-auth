from django.contrib.auth.hashers import identify_hasher

from django_offline_auth.exceptions import CredentialGenerationError


class DjangoPasswordCredentialProvider:
    def get_verifier(self, user) -> str:
        verifier = getattr(user, "password", None)

        if not verifier:
            raise CredentialGenerationError("User does not have a password verifier.")

        if not isinstance(verifier, str):
            raise CredentialGenerationError("User password verifier must be a string.")

        try:
            identify_hasher(verifier)
        except Exception as exc:
            raise CredentialGenerationError(
                "User password verifier is not a valid Django password hash."
            ) from exc

        return verifier
