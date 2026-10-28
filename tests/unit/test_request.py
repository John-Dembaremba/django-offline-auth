import pytest
from pydantic import ValidationError

from django_offline_auth.protocol.requests import (
    OfflineCredentialSyncRequest,
)


def test_sync_request_accepts_public_key():
    request = OfflineCredentialSyncRequest(
        public_key="test-public-key",
    )

    assert request.public_key == "test-public-key"


def test_sync_request_requires_public_key():
    with pytest.raises(ValidationError):
        OfflineCredentialSyncRequest(
            public_key="",
        )


def test_sync_request_rejects_oversized_public_key():
    with pytest.raises(ValidationError):
        OfflineCredentialSyncRequest(
            public_key="a" * 8193,
        )
