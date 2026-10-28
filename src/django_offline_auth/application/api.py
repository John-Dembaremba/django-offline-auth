from collections.abc import Iterable
from datetime import timedelta
from typing import Any

from django_offline_auth.application.services.issue_credentials import (
    IssueOfflineCredentials,
)
from django_offline_auth.conf import get_credential_ttl
from django_offline_auth.infrastructure.credential_provider import (
    DjangoPasswordCredentialProvider,
)
from django_offline_auth.infrastructure.crypto.envelope import (
    RSAOAEPEnvelopeEncryptor,
)
from django_offline_auth.protocol.payloads import (
    OfflineCredentialSnapshot,
)


def _validate_ttl(ttl: timedelta) -> timedelta:
    """Validate an offline credential lifetime."""
    if ttl <= timedelta(0):
        raise ValueError("ttl must be greater than 0.")

    return ttl


def issue_offline_credentials(
    *,
    users: Iterable[Any],
    public_key: str,
    ttl: timedelta | None = None,
) -> OfflineCredentialSnapshot:
    """
    Issue encrypted offline credentials for eligible users.

    Args:
        users: Django users to evaluate for offline authentication.
        public_key: Base64-encoded RSA public key from the mobile client.
        ttl: Optional credential lifetime. Uses the configured default if omitted.

    Returns:
        OfflineCredentialSnapshot:
            Encrypted credential snapshot containing:
            - protocol_version
            - credentials.

            `credentials` contains:
            - user_id
            - username
            - envelope

            `envelope` contains:
            - key_algorithm
            - content_algorithm
            - encrypted_key
            - nonce
            - ciphertext

    Raises:
        InvalidPublicKeyError: If the public key is invalid or unsupported.
        CredentialGenerationError: If a user verifier cannot be generated.
        ValidationError: If generated credential data is invalid.
    """
    credential_ttl = _validate_ttl(ttl) if ttl is not None else get_credential_ttl()

    service = IssueOfflineCredentials(
        credential_provider=DjangoPasswordCredentialProvider(),
        encryptor=RSAOAEPEnvelopeEncryptor(),
    )

    return service.execute(
        users=users,
        public_key=public_key,
        ttl=credential_ttl,
    )
