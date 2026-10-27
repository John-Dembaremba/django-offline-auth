import base64
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from django_offline_auth.exceptions import InvalidPublicKeyError
from django_offline_auth.protocol.constants import (
    CONTENT_ALGORITHM_AES_256_GCM,
    KEY_ALGORITHM_RSA_OAEP_SHA256,
)
from django_offline_auth.protocol.payloads import EncryptedCredentialEnvelope


class RSAOAEPEnvelopeEncryptor:
    """Encrypt credential payloads using AES-GCM and RSA-OAEP."""

    def encrypt(
        self,
        *,
        public_key: str,
        plaintext: bytes,
    ) -> EncryptedCredentialEnvelope:
        rsa_public_key = self._load_public_key(public_key)

        aes_key = AESGCM.generate_key(bit_length=256)
        nonce = os.urandom(12)

        aesgcm = AESGCM(aes_key)

        ciphertext = aesgcm.encrypt(
            nonce,
            plaintext,
            None,
        )

        encrypted_key = rsa_public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(
                    algorithm=hashes.SHA256(),
                ),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        return EncryptedCredentialEnvelope(
            key_algorithm=KEY_ALGORITHM_RSA_OAEP_SHA256,
            content_algorithm=CONTENT_ALGORITHM_AES_256_GCM,
            encrypted_key=self._b64(encrypted_key),
            nonce=self._b64(nonce),
            ciphertext=self._b64(ciphertext),
        )

    def _load_public_key(
        self,
        public_key: str,
    ) -> rsa.RSAPublicKey:
        try:
            public_key_bytes = base64.b64decode(
                public_key,
                validate=True,
            )

            loaded_key = serialization.load_der_public_key(
                public_key_bytes,
            )
        except (ValueError, TypeError) as exc:
            raise InvalidPublicKeyError("Invalid public key.") from exc

        if not isinstance(loaded_key, rsa.RSAPublicKey):
            raise InvalidPublicKeyError("Public key must be an RSA public key.")

        if loaded_key.key_size < 2048:
            raise InvalidPublicKeyError("RSA public key must be at least 2048 bits.")

        return loaded_key

    @staticmethod
    def _b64(value: bytes) -> str:
        return base64.b64encode(value).decode("ascii")
