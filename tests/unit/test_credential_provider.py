import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from django_offline_auth.exceptions import CredentialGenerationError
from django_offline_auth.infrastructure.credential_provider import (
    DjangoPasswordCredentialProvider,
)
from django_offline_auth.protocol.constants import (
    PASSWORD_ALGORITHM_PBKDF2_SHA256,
    SUPPORTED_PASSWORD_ALGORITHMS,
)

pytestmark = pytest.mark.django_db


def test_get_verifier_returns_django_password_hash_pbkdf2_sha256():
    User = get_user_model()

    user = User.objects.create_user(username="John Wick", password="myStrongPsw")

    provider = DjangoPasswordCredentialProvider()
    verifier = provider.get_verifier(user)

    assert verifier == user.password
    assert verifier.startswith("pbkdf2_sha256")


def test_get_verifier_rejects_empty_password():
    User = get_user_model()

    user = User.objects.create(
        username="john",
        password="",
    )

    provider = DjangoPasswordCredentialProvider()

    with pytest.raises(CredentialGenerationError):
        provider.get_verifier(user)


def test_get_verifier_rejects_invalid_hash():
    User = get_user_model()

    user = User.objects.create(
        username="john",
        password="not-a-valid-django-hash",
    )

    provider = DjangoPasswordCredentialProvider()

    with pytest.raises(CredentialGenerationError):
        provider.get_verifier(user)


def test_get_verifier_rejects_unsupported_algorithm():
    User = get_user_model()

    user = User.objects.create(
        username="john",
        password=make_password(
            "secret123",
            hasher="scrypt",
        ),
    )

    provider = DjangoPasswordCredentialProvider()

    with pytest.raises(
        CredentialGenerationError,
        match="Unsupported password algorithm",
    ):
        provider.get_verifier(user)


def test_protocol_supports_pbkdf2_sha256():
    assert PASSWORD_ALGORITHM_PBKDF2_SHA256 in SUPPORTED_PASSWORD_ALGORITHMS


def test_get_verifier_rejects_unusable_password():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
    )

    user.set_unusable_password()
    user.save(update_fields=["password"])

    provider = DjangoPasswordCredentialProvider()

    with pytest.raises(
        CredentialGenerationError,
        match="does not have a usable password",
    ):
        provider.get_verifier(user)
