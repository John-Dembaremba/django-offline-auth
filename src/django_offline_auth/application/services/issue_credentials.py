from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from django_offline_auth.application.interfaces.credential_provider import (
    CredentialProvider,
)
from django_offline_auth.application.interfaces.envelope_encryptor import (
    EnvelopeEncryptor,
)
from django_offline_auth.models import OfflineAuth
from django_offline_auth.protocol.constants import PROTOCOL_VERSION
from django_offline_auth.protocol.payloads import (
    OfflineCredentialItem,
    OfflineCredentialPayload,
    OfflineCredentialSnapshot,
)


class IssueOfflineCredentials:
    """Build and encrypt offline credentials for eligible users. User that ain`t active are excluded"""

    def __init__(
        self,
        credential_provider: CredentialProvider,
        encryptor: EnvelopeEncryptor,
    ) -> None:
        self.credential_provider = credential_provider
        self.encryptor = encryptor

    def execute(
        self,
        *,
        users: Iterable,
        public_key: str,
        ttl: timedelta,
    ) -> OfflineCredentialSnapshot:
        issued_at = datetime.now(UTC)
        expires_at = issued_at + ttl

        credentials: list[OfflineCredentialItem] = []

        for user in users:
            offline_auth = OfflineAuth.objects.filter(
                user=user,
                is_enabled=True,
            ).first()

            if offline_auth is None:
                continue

            if not user.is_active:
                continue

            verifier = self.credential_provider.get_verifier(user)

            payload = OfflineCredentialPayload(
                protocol_version=PROTOCOL_VERSION,
                user_id=str(user.pk),
                username=user.get_username(),
                verifier=verifier,
                issued_at=issued_at,
                expires_at=expires_at,
                credential_version=offline_auth.credential_version,
            )

            envelope = self.encryptor.encrypt(
                public_key=public_key,
                plaintext=payload.to_bytes(),
            )

            credentials.append(
                OfflineCredentialItem(
                    user_id=str(user.pk),
                    username=user.get_username(),
                    envelope=envelope,
                )
            )

        return OfflineCredentialSnapshot(
            protocol_version=PROTOCOL_VERSION,
            credentials=credentials,
        )
