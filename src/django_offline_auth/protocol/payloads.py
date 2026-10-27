from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OfflineCredentialPayload(BaseModel):
    """Plaintext offline credential payload before encryption."""

    model_config = ConfigDict(frozen=True)

    protocol_version: int = Field(ge=1)
    user_id: str = Field(min_length=1)
    username: str = Field(min_length=1)
    verifier: str = Field(min_length=1)
    issued_at: datetime
    expires_at: datetime
    credential_version: int = Field(ge=1)

    @field_validator("issued_at", "expires_at")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        """Require timezone-aware timestamps."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")

        return value

    @model_validator(mode="after")
    def validate_expiry(self) -> "OfflineCredentialPayload":
        """Require expiry to be later than issue time."""
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be later than issued_at")

        return self

    def to_bytes(self) -> bytes:
        """Return the payload as UTF-8 JSON bytes for encryption."""
        return self.model_dump_json().encode("utf-8")


class EncryptedCredentialEnvelope(BaseModel):
    """Encrypted credential payload sent to the client."""

    model_config = ConfigDict(frozen=True)

    key_algorithm: str
    content_algorithm: str
    encrypted_key: str
    nonce: str
    ciphertext: str


class OfflineCredentialItem(BaseModel):
    """Encrypted offline credential for one user."""

    model_config = ConfigDict(frozen=True)

    user_id: str
    username: str
    envelope: EncryptedCredentialEnvelope


class OfflineCredentialSnapshot(BaseModel):
    """Authoritative set of offline credentials returned to the client."""

    model_config = ConfigDict(frozen=True)

    protocol_version: int
    credentials: list[OfflineCredentialItem]
