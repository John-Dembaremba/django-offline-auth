from typing import Any, Protocol


class CredentialProvider(Protocol):
    def get_verifier(self, user: Any) -> str: ...
