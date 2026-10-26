import json
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class OfflineCredentialPayload:
    """Plaintext offline credential payload before encryption."""

    protocol_version: int
    user_id: str
    username: str
    verifier: str
    issued_at: datetime
    expires_at: datetime
    credential_version: int

    def to_dict(self) -> dict:
        """Return the payload as a JSON-serializable dictionary."""
        return {
            "protocol_version": self.protocol_version,
            "user_id": self.user_id,
            "username": self.username,
            "verifier": self.verifier,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "credential_version": self.credential_version,
        }

    def to_bytes(self) -> bytes:
        """Return the payload as UTF-8 JSON bytes for encryption."""
        return json.dumps(
            self.to_dict(),
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
