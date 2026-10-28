from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model

from django_offline_auth.application.services.issue_credentials import (
    IssueOfflineCredentials,
)
from django_offline_auth.models import OfflineAuth
from django_offline_auth.protocol.payloads import EncryptedCredentialEnvelope

pytestmark = pytest.mark.django_db


class FakeCredentialProvider:
    def get_verifier(self, user) -> str:
        return f"verifier-for-{user.username}"


class FakeEncryptor:
    def encrypt(
        self,
        *,
        public_key: str,
        plaintext: bytes,
    ) -> EncryptedCredentialEnvelope:
        return EncryptedCredentialEnvelope(
            key_algorithm="RSA-OAEP-256",
            content_algorithm="A256GCM",
            encrypted_key="encrypted-key",
            nonce="nonce",
            ciphertext="ciphertext",
        )


def test_issue_credentials_returns_enabled_users():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    service = IssueOfflineCredentials(
        credential_provider=FakeCredentialProvider(),
        encryptor=FakeEncryptor(),
    )

    result = service.execute(
        users=[user],
        public_key="public-key",
        ttl=timedelta(hours=24),
    )

    assert result.protocol_version == 1
    assert len(result.credentials) == 1

    credential = result.credentials[0]

    assert credential.user_id == str(user.pk)
    assert credential.username == "mary"
    assert credential.envelope.key_algorithm == "RSA-OAEP-256"


def test_issue_credentials_skips_disabled_users():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=False,
    )

    service = IssueOfflineCredentials(
        credential_provider=FakeCredentialProvider(),
        encryptor=FakeEncryptor(),
    )

    result = service.execute(
        users=[user],
        public_key="public-key",
        ttl=timedelta(hours=24),
    )

    assert result.credentials == []


def test_issue_credentials_skips_users_without_offline_auth():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    service = IssueOfflineCredentials(
        credential_provider=FakeCredentialProvider(),
        encryptor=FakeEncryptor(),
    )

    result = service.execute(
        users=[user],
        public_key="public-key",
        ttl=timedelta(hours=24),
    )

    assert result.credentials == []
