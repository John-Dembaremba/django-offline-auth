from collections.abc import Iterable
from datetime import timedelta
from typing import Any

from django_offline_auth.application.services.issue_credentials import (
    IssueOfflineCredentials,
)
from django_offline_auth.infrastructure.credential_provider import (
    DjangoPasswordCredentialProvider,
)
from django_offline_auth.infrastructure.crypto.envelope import (
    RSAOAEPEnvelopeEncryptor,
)
from django_offline_auth.protocol.constants import (
    DEFAULT_CREDENTIAL_TTL_SECONDS,
)
from django_offline_auth.protocol.payloads import (
    OfflineCredentialSnapshot,
)


def issue_offline_credentials(
    *,
    users: Iterable[Any],
    public_key: str,
    ttl: timedelta | None = None,
) -> OfflineCredentialSnapshot:
    """Issue encrypted offline credentials for eligible users."""

    credential_ttl = ttl or timedelta(
        seconds=DEFAULT_CREDENTIAL_TTL_SECONDS,
    )

    service = IssueOfflineCredentials(
        credential_provider=DjangoPasswordCredentialProvider(),
        encryptor=RSAOAEPEnvelopeEncryptor(),
    )

    return service.execute(
        users=users,
        public_key=public_key,
        ttl=credential_ttl,
    )
