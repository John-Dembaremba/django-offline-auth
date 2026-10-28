import base64
import json
from datetime import datetime, timedelta

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.contrib.auth import get_user_model
from django.test import override_settings

from django_offline_auth.application import issue_offline_credentials
from django_offline_auth.models import OfflineAuth

pytestmark = pytest.mark.django_db


def generate_rsa_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    public_key_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    public_key_b64 = base64.b64encode(public_key_der).decode("ascii")

    return private_key, public_key_b64


def decrypt_envelope(private_key, envelope):
    encrypted_key = base64.b64decode(envelope.encrypted_key)

    nonce = base64.b64decode(envelope.nonce)

    ciphertext = base64.b64decode(envelope.ciphertext)

    aes_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(
                algorithm=hashes.SHA256(),
            ),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    plaintext = AESGCM(aes_key).decrypt(
        nonce,
        ciphertext,
        None,
    )

    return json.loads(plaintext.decode("utf-8"))


def decrypt_payload(private_key, snapshot):
    credential = snapshot.credentials[0]

    return decrypt_envelope(
        private_key,
        credential.envelope,
    )


def test_offline_credential_can_be_decrypted():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    private_key, public_key = generate_rsa_key_pair()

    snapshot = issue_offline_credentials(
        users=[user],
        public_key=public_key,
    )

    credential = snapshot.credentials[0]

    payload = decrypt_envelope(
        private_key,
        credential.envelope,
    )

    assert payload["user_id"] == str(user.pk)
    assert payload["username"] == user.username
    assert payload["verifier"] == user.password
    assert payload["protocol_version"] == 1
    assert payload["credential_version"] == 1


def test_password_verifier_is_not_exposed_in_snapshot():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    _, public_key = generate_rsa_key_pair()

    snapshot = issue_offline_credentials(
        users=[user],
        public_key=public_key,
    )

    serialized = snapshot.model_dump_json()

    assert user.password not in serialized


def test_wrong_private_key_cannot_decrypt_credential():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    _, public_key = generate_rsa_key_pair()
    wrong_private_key, _ = generate_rsa_key_pair()

    snapshot = issue_offline_credentials(
        users=[user],
        public_key=public_key,
    )

    credential = snapshot.credentials[0]

    with pytest.raises(ValueError):
        decrypt_envelope(
            wrong_private_key,
            credential.envelope,
        )


def test_tampered_ciphertext_is_rejected():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    private_key, public_key = generate_rsa_key_pair()

    snapshot = issue_offline_credentials(
        users=[user],
        public_key=public_key,
    )

    envelope = snapshot.credentials[0].envelope

    ciphertext = bytearray(base64.b64decode(envelope.ciphertext))

    ciphertext[0] ^= 1

    tampered_envelope = envelope.model_copy(
        update={"ciphertext": base64.b64encode(bytes(ciphertext)).decode("ascii")}
    )

    with pytest.raises(InvalidTag):
        decrypt_envelope(
            private_key,
            tampered_envelope,
        )


def test_tampered_nonce_is_rejected():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    private_key, public_key = generate_rsa_key_pair()

    snapshot = issue_offline_credentials(
        users=[user],
        public_key=public_key,
    )

    envelope = snapshot.credentials[0].envelope

    nonce = bytearray(base64.b64decode(envelope.nonce))

    nonce[0] ^= 1

    tampered_envelope = envelope.model_copy(
        update={"nonce": base64.b64encode(bytes(nonce)).decode("ascii")}
    )

    with pytest.raises(InvalidTag):
        decrypt_envelope(
            private_key,
            tampered_envelope,
        )


def test_tampered_encrypted_key_is_rejected():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    private_key, public_key = generate_rsa_key_pair()

    snapshot = issue_offline_credentials(
        users=[user],
        public_key=public_key,
    )

    envelope = snapshot.credentials[0].envelope

    encrypted_key = bytearray(base64.b64decode(envelope.encrypted_key))

    encrypted_key[0] ^= 1

    tampered_envelope = envelope.model_copy(
        update={"encrypted_key": base64.b64encode(bytes(encrypted_key)).decode("ascii")}
    )

    with pytest.raises(ValueError):
        decrypt_envelope(
            private_key,
            tampered_envelope,
        )


def test_same_credential_produces_different_ciphertext():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    _, public_key = generate_rsa_key_pair()

    first_snapshot = issue_offline_credentials(
        users=[user],
        public_key=public_key,
    )

    second_snapshot = issue_offline_credentials(
        users=[user],
        public_key=public_key,
    )

    first_envelope = first_snapshot.credentials[0].envelope
    second_envelope = second_snapshot.credentials[0].envelope

    assert first_envelope.encrypted_key != second_envelope.encrypted_key
    assert first_envelope.nonce != second_envelope.nonce
    assert first_envelope.ciphertext != second_envelope.ciphertext


@override_settings(
    DJANGO_OFFLINE_AUTH_CREDENTIAL_TTL_SECONDS=3600,
)
def test_snapshot_uses_configured_credential_ttl():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    private_key, public_key = generate_rsa_key_pair()

    snapshot = issue_offline_credentials(
        users=[user],
        public_key=public_key,
    )

    payload = decrypt_payload(
        private_key,
        snapshot,
    )

    issued_at = datetime.fromisoformat(
        payload["issued_at"],
    )

    expires_at = datetime.fromisoformat(
        payload["expires_at"],
    )

    assert expires_at - issued_at == timedelta(hours=1)


@override_settings(
    DJANGO_OFFLINE_AUTH_CREDENTIAL_TTL_SECONDS=3600,
)
def test_explicit_ttl_overrides_configured_ttl():
    User = get_user_model()

    user = User.objects.create_user(
        username="mary",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    private_key, public_key = generate_rsa_key_pair()

    snapshot = issue_offline_credentials(
        users=[user],
        public_key=public_key,
        ttl=timedelta(minutes=30),
    )

    payload = decrypt_payload(
        private_key,
        snapshot,
    )

    issued_at = datetime.fromisoformat(
        payload["issued_at"],
    )

    expires_at = datetime.fromisoformat(
        payload["expires_at"],
    )

    assert expires_at - issued_at == timedelta(minutes=30)


def test_explicit_ttl_must_be_positive():
    _, public_key = generate_rsa_key_pair()

    with pytest.raises(
        ValueError,
        match="ttl must be greater than 0",
    ):
        issue_offline_credentials(
            users=[],
            public_key=public_key,
            ttl=timedelta(0),
        )


def test_negative_explicit_ttl_is_rejected():
    _, public_key = generate_rsa_key_pair()

    with pytest.raises(
        ValueError,
        match="ttl must be greater than 0",
    ):
        issue_offline_credentials(
            users=[],
            public_key=public_key,
            ttl=timedelta(seconds=-1),
        )
