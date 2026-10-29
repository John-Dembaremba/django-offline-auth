class OfflineAuthError(Exception):
    """Base exception for django-offline-auth."""


class OfflineAuthDisabledError(OfflineAuthError):
    """Raised when offline authentication is disabled for a user."""


class InvalidPublicKeyError(OfflineAuthError):
    """Raised when the supplied public key is invalid or unsupported."""


class UnsupportedProtocolError(OfflineAuthError):
    """Raised when the requested protocol version is unsupported."""


class CredentialGenerationError(OfflineAuthError):
    """Raised when an offline credential cannot be generated."""


class OfflineAuthError(Exception):
    """Base exception for offline authentication."""


class UnusablePasswordError(CredentialGenerationError):
    """User does not have a usable password."""


class UnsupportedPasswordAlgorithmError(CredentialGenerationError):
    """User password algorithm is not supported."""


class InvalidPasswordVerifierError(CredentialGenerationError):
    """User password verifier is invalid."""
