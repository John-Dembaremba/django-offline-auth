from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from django_offline_auth.protocol.payloads import (
    OfflineCredentialPayload,
)


def make_payload(**overrides):
    issued_at = datetime(
        2026,
        10,
        26,
        10,
        0,
        tzinfo=UTC,
    )

    values = {
        "protocol_version": 1,
        "user_id": "42",
        "username": "mary",
        "verifier": "pbkdf2_sha256$1000000$salt$hash",
        "issued_at": issued_at,
        "expires_at": issued_at + timedelta(hours=24),
        "credential_version": 1,
    }

    values.update(overrides)

    return OfflineCredentialPayload(**values)


def test_payload_is_valid():
    payload = make_payload()

    assert payload.username == "mary"
    assert payload.protocol_version == 1


def test_payload_requires_username():
    with pytest.raises(ValidationError):
        make_payload(username="")


def test_payload_requires_verifier():
    with pytest.raises(ValidationError):
        make_payload(verifier="")


def test_payload_requires_positive_protocol_version():
    with pytest.raises(ValidationError):
        make_payload(protocol_version=0)


def test_payload_requires_positive_credential_version():
    with pytest.raises(ValidationError):
        make_payload(credential_version=0)


def test_payload_requires_timezone_aware_timestamp():
    with pytest.raises(ValidationError):
        make_payload(
            issued_at="2026-10-26T10:00:00",
        )


def test_payload_expiry_must_be_after_issue_time():
    issued_at = datetime(
        2026,
        10,
        26,
        10,
        0,
        tzinfo=UTC,
    )

    with pytest.raises(ValidationError):
        make_payload(
            issued_at=issued_at,
            expires_at=issued_at,
        )
