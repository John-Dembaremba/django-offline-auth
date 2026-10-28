from pydantic import BaseModel, ConfigDict, Field


class OfflineCredentialSyncRequest(BaseModel):
    """Offline credential synchronization request."""

    model_config = ConfigDict(frozen=True)

    public_key: str = Field(
        min_length=1,
        max_length=8192,
    )
