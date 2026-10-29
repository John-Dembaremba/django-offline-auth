import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from django_offline_auth.application import issue_offline_credentials
from django_offline_auth.models import OfflineAuth
from django_offline_auth.protocol.constants import (
    FAILURE_REASON_INVALID_PASSWORD_VERIFIER,
    FAILURE_REASON_UNSUPPORTED_PASSWORD_ALGORITHM,
    FAILURE_REASON_UNUSABLE_PASSWORD,
)

pytestmark = pytest.mark.django_db


def generate_public_key() -> str:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    public_key_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return base64.b64encode(
        public_key_der,
    ).decode("ascii")


def test_issue_offline_credentials():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
    )

    snapshot = issue_offline_credentials(
        users=[user],
        public_key=generate_public_key(),
    )

    assert snapshot.protocol_version == 1
    assert len(snapshot.credentials) == 1

    credential = snapshot.credentials[0]

    assert credential.user_id == str(user.pk)
    assert credential.username == "mary"

    assert credential.envelope.encrypted_key
    assert credential.envelope.nonce
    assert credential.envelope.ciphertext

    serialized = snapshot.model_dump_json()
    assert user.password not in serialized


def test_inactive_users_not_issued_credential():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary", password="secret123", is_active=False
    )

    OfflineAuth.objects.create(
        user=user,
    )

    snapshot = issue_offline_credentials(
        users=[user],
        public_key=generate_public_key(),
    )

    assert len(snapshot.credentials) == 0


def test_snapshot_excludes_inactive_users():
    User = get_user_model()

    active_user = User.objects.create_user(
        username="mary",
        password="secret123",
        is_active=True,
    )

    inactive_user = User.objects.create_user(
        username="john",
        password="secret123",
        is_active=False,
    )

    OfflineAuth.objects.create(
        user=active_user,
        is_enabled=True,
    )

    OfflineAuth.objects.create(
        user=inactive_user,
        is_enabled=True,
    )

    public_key = generate_public_key()

    snapshot = issue_offline_credentials(
        users=[active_user, inactive_user],
        public_key=public_key,
    )

    assert len(snapshot.credentials) == 1
    assert snapshot.credentials[0].user_id == str(active_user.pk)


def test_user_failure_does_not_stop_other_credentials():
    User = get_user_model()

    valid_user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    invalid_user = User.objects.create_user(
        username="john",
    )
    invalid_user.set_unusable_password()
    invalid_user.save(update_fields=["password"])

    OfflineAuth.objects.create(
        user=valid_user,
        is_enabled=True,
    )

    OfflineAuth.objects.create(
        user=invalid_user,
        is_enabled=True,
    )

    snapshot = issue_offline_credentials(
        users=[valid_user, invalid_user],
        public_key=generate_public_key(),
    )

    assert len(snapshot.credentials) == 1
    assert len(snapshot.failures) == 1

    credential = snapshot.credentials[0]

    assert credential.user_id == str(valid_user.pk)
    assert credential.username == valid_user.username

    failure = snapshot.failures[0]

    assert failure.user_id == str(invalid_user.pk)
    assert failure.username == invalid_user.username
    assert failure.reason == FAILURE_REASON_UNUSABLE_PASSWORD


def test_snapshot_can_contain_only_failures():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    snapshot = issue_offline_credentials(
        users=[user],
        public_key=generate_public_key(),
    )

    assert snapshot.credentials == []
    assert len(snapshot.failures) == 1

    failure = snapshot.failures[0]

    assert failure.user_id == str(user.pk)
    assert failure.username == user.username
    assert failure.reason == FAILURE_REASON_UNUSABLE_PASSWORD


def test_unsupported_password_algorithm_is_reported():
    User = get_user_model()

    valid_user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    unsupported_user = User.objects.create(
        username="john",
        password=make_password(
            "secret123",
            hasher="scrypt",
        ),
    )

    OfflineAuth.objects.create(
        user=valid_user,
        is_enabled=True,
    )

    OfflineAuth.objects.create(
        user=unsupported_user,
        is_enabled=True,
    )

    snapshot = issue_offline_credentials(
        users=[valid_user, unsupported_user],
        public_key=generate_public_key(),
    )

    assert len(snapshot.credentials) == 1
    assert len(snapshot.failures) == 1

    credential = snapshot.credentials[0]

    assert credential.user_id == str(valid_user.pk)
    assert credential.username == valid_user.username

    failure = snapshot.failures[0]

    assert failure.user_id == str(unsupported_user.pk)
    assert failure.username == unsupported_user.username
    assert failure.reason == FAILURE_REASON_UNSUPPORTED_PASSWORD_ALGORITHM


def test_snapshot_reports_unsupported_algorithm_failure():
    User = get_user_model()

    user = User.objects.create(
        username="john",
        password=make_password(
            "secret123",
            hasher="scrypt",
        ),
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    snapshot = issue_offline_credentials(
        users=[user],
        public_key=generate_public_key(),
    )

    assert snapshot.credentials == []
    assert len(snapshot.failures) == 1

    assert snapshot.failures[0].reason == FAILURE_REASON_UNSUPPORTED_PASSWORD_ALGORITHM


def test_invalid_password_verifier_is_reported():
    User = get_user_model()

    valid_user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    invalid_user = User.objects.create(
        username="john",
        password="this-is-not-a-valid-django-password-hash",
    )

    OfflineAuth.objects.create(
        user=valid_user,
        is_enabled=True,
    )

    OfflineAuth.objects.create(
        user=invalid_user,
        is_enabled=True,
    )

    snapshot = issue_offline_credentials(
        users=[valid_user, invalid_user],
        public_key=generate_public_key(),
    )

    assert len(snapshot.credentials) == 1
    assert len(snapshot.failures) == 1

    credential = snapshot.credentials[0]

    assert credential.user_id == str(valid_user.pk)
    assert credential.username == valid_user.username

    failure = snapshot.failures[0]

    assert failure.user_id == str(invalid_user.pk)
    assert failure.username == invalid_user.username
    assert failure.reason == FAILURE_REASON_INVALID_PASSWORD_VERIFIER
