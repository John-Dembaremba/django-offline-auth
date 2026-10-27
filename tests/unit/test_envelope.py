import base64

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from django_offline_auth.exceptions import InvalidPublicKeyError
from django_offline_auth.infrastructure.crypto.envelope import (
    RSAOAEPEnvelopeEncryptor,
)


def generate_rsa_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    public_key = private_key.public_key()

    public_key_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    public_key_b64 = base64.b64encode(public_key_der).decode("ascii")

    return private_key, public_key_b64


def test_encrypt_returns_decryptable_envelope():
    private_key, public_key = generate_rsa_key_pair()

    plaintext = b"offline credential payload"

    encryptor = RSAOAEPEnvelopeEncryptor()

    envelope = encryptor.encrypt(
        public_key=public_key,
        plaintext=plaintext,
    )

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

    decrypted = AESGCM(aes_key).decrypt(
        nonce,
        ciphertext,
        None,
    )

    assert decrypted == plaintext


def test_encrypt_uses_expected_algorithms():
    _, public_key = generate_rsa_key_pair()

    encryptor = RSAOAEPEnvelopeEncryptor()

    envelope = encryptor.encrypt(
        public_key=public_key,
        plaintext=b"test",
    )

    assert envelope.key_algorithm == "RSA-OAEP-256"
    assert envelope.content_algorithm == "A256GCM"


def test_encrypt_rejects_invalid_base64_key():
    encryptor = RSAOAEPEnvelopeEncryptor()

    with pytest.raises(InvalidPublicKeyError):
        encryptor.encrypt(
            public_key="not-valid-base64!!!",
            plaintext=b"test",
        )


def test_encrypt_rejects_small_rsa_key():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=1024,
    )

    public_key_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    public_key = base64.b64encode(public_key_der).decode("ascii")

    encryptor = RSAOAEPEnvelopeEncryptor()

    with pytest.raises(InvalidPublicKeyError):
        encryptor.encrypt(
            public_key=public_key,
            plaintext=b"test",
        )
