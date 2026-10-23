import pytest
from django.contrib.auth import get_user_model

from django_offline_auth.exceptions import CredentialGenerationError
from django_offline_auth.infrastructure.credential_provider import (
    DjangoPasswordCredentialProvider,
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
