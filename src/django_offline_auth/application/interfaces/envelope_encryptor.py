from typing import Protocol

from django_offline_auth.protocol.payloads import (
    EncryptedCredentialEnvelope,
)


class EnvelopeEncryptor(Protocol):
    """Encrypts credential payloads for a mobile client."""

    def encrypt(
        self,
        *,
        public_key: str,
        plaintext: bytes,
    ) -> EncryptedCredentialEnvelope: ...
