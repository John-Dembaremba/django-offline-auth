import json
from datetime import UTC, datetime

from django_offline_auth.protocol.payloads import OfflineCredentialPayload


def test_offline_credential_payload_to_dict():
    issued_at = datetime(
        2026,
        10,
        23,
        8,
        30,
        tzinfo=UTC,
    )

    expires_at = datetime(
        2026,
        10,
        24,
        8,
        30,
        tzinfo=UTC,
    )

    payload = OfflineCredentialPayload(
        protocol_version=1,
        user_id="42",
        username="mary",
        verifier="pbkdf2_sha256$1000000$salt$hash",
        issued_at=issued_at,
        expires_at=expires_at,
        credential_version=1,
    )

    result = payload.to_dict()

    assert result == {
        "protocol_version": 1,
        "user_id": "42",
        "username": "mary",
        "verifier": "pbkdf2_sha256$1000000$salt$hash",
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "credential_version": 1,
    }


def test_offline_credential_payload_to_bytes():
    issued_at = datetime(
        2026,
        10,
        23,
        8,
        30,
        tzinfo=UTC,
    )

    expires_at = datetime(
        2026,
        10,
        24,
        8,
        30,
        tzinfo=UTC,
    )

    payload = OfflineCredentialPayload(
        protocol_version=1,
        user_id="42",
        username="mary",
        verifier="pbkdf2_sha256$1000000$salt$hash",
        issued_at=issued_at,
        expires_at=expires_at,
        credential_version=1,
    )

    result = payload.to_bytes()

    decoded = json.loads(result.decode("utf-8"))

    assert decoded["protocol_version"] == 1
    assert decoded["user_id"] == "42"
    assert decoded["username"] == "mary"
    assert decoded["verifier"] == ("pbkdf2_sha256$1000000$salt$hash")
    assert decoded["credential_version"] == 1
