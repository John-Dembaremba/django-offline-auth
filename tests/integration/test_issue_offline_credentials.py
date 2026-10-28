import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import get_user_model

from django_offline_auth.application import issue_offline_credentials
from django_offline_auth.models import OfflineAuth

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
