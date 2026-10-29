# django-offline-auth

Reusable Django package for securely issuing offline authentication credentials to mobile applications.

The package is intentionally **user-centric and device-agnostic on the Django side**.

It does not store:

- device IDs;
- device names;
- IMEI numbers;
- asset relationships;
- Android private keys.

The host Django application decides which users are eligible for offline authentication.

`django-offline-auth` securely prepares and encrypts their offline credentials.

## Architecture

```text
Host Django Application
        │
        │ decides WHO can authenticate offline
        ▼
django-offline-auth
        │
        │ packages + encrypts credentials
        ▼
Android Application
        │
        │ protects keys with Android Keystore
        ▼
Offline Authentication
```

The Django backend remains user-centric.

The Android application protects downloaded credentials using an installation-local private key stored in Android Keystore.

## Installation

Install the package into the host Django project.

```bash
pip install django-offline-auth
```

For local development:

```bash
pip install -e .
```

Add the package to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "django_offline_auth",
]
```

Run migrations:

```bash
python manage.py migrate
```

## OfflineAuth Model

The package stores one `OfflineAuth` record per Django user.

The model tracks:

```text
user
is_enabled
credential_version
created_at
updated_at
```

The package does **not** store another copy of the user's password verifier.

`user.password` remains the source of truth.

A user is eligible for credential issuance only when:

```text
user.is_active = True
AND
OfflineAuth exists
AND
OfflineAuth.is_enabled = True
```

## Enabling and Disabling Offline Authentication

The host application decides when a user should be enrolled.

Use the package application API:

```python
from django_offline_auth.application import enable_offline_auth

enable_offline_auth(user)
```

Disable offline authentication with:

```python
from django_offline_auth.application import disable_offline_auth

disable_offline_auth(user)
```

Explicit credential rotation is also available:

```python
from django_offline_auth.application import rotate_offline_credentials

rotate_offline_credentials(user)
```

`credential_version` represents the generation of the user's offline-authentication state.

It is incremented when credentials are explicitly rotated or when offline authentication is disabled and later re-enabled.

Normal synchronization does not increment the version.

## Main Flow

```text
ONLINE

User logs in normally
        ↓
Django returns JWT
        ↓
Host application determines eligible offline users
        ↓
Android sends its public key
        ↓
django-offline-auth reads each user's
current Django password verifier
        ↓
Credential payload is encrypted
        ↓
Encrypted credentials are downloaded
and stored locally


OFFLINE

User enters username + password
        ↓
Android finds that user's downloaded credential
        ↓
Android Keystore private key decrypts the credential
        ↓
Django password verifier is recovered
inside native code
        ↓
PBKDF2 verification runs locally
        ↓
Success / Failure
```

JWT issuance and offline credential synchronization are intentionally separate.

A Django password verifier must never be included in a JWT.

## Issuing Offline Credentials

The main public API is:

```python
from django_offline_auth.application import issue_offline_credentials
```

Example:

```python
snapshot = issue_offline_credentials(
    users=eligible_users,
    public_key=android_public_key,
)
```

The package receives:

```text
users
    Django user objects selected by the host application

public_key
    Base64-encoded RSA public key supplied by the Android client
```

The package returns an `OfflineCredentialSnapshot`.

Example:

```json
{
  "protocol_version": 1,
  "credentials": [
    {
      "user_id": "1",
      "username": "mary",
      "envelope": {
        "key_algorithm": "RSA-OAEP-256",
        "content_algorithm": "A256GCM",
        "encrypted_key": "...",
        "nonce": "...",
        "ciphertext": "..."
      }
    }
  ],
  "failures": [
    {
      "user_id": "2",
      "username": "john",
      "reason": "unusable_password"
    }
  ]
}
```

The encrypted payload contains the sensitive password verifier.

The outer response does not expose it.

## Host Application Integration

The package does not decide which users should be available offline.

A host application may use any business logic it needs:

```python
eligible_users = determine_eligible_users(request.user)

snapshot = issue_offline_credentials(
    users=eligible_users,
    public_key=public_key,
)
```

The host application is responsible for:

```text
authentication
authorization
business rules
user selection
API endpoint integration
```

The package is responsible for securely generating credentials for the supplied users.

The client should never be allowed to submit arbitrary user IDs and decide who receives offline credentials.

## Request Validation

The package provides a request model for basic synchronization input validation.

```python
from django_offline_auth.protocol.requests import (
    OfflineCredentialSyncRequest,
)

sync_request = OfflineCredentialSyncRequest.model_validate(
    request.data
)
```

Example request:

```json
{
  "public_key": "MIIBIjANBgkqh..."
}
```

The package validates the request structure separately from cryptographic public-key validation.

## Example DRF Integration

The package itself does not depend on Django REST Framework.

A host application can integrate it with DRF like this:

```python
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_offline_auth.application import issue_offline_credentials
from django_offline_auth.protocol.requests import (
    OfflineCredentialSyncRequest,
)


class OfflineCredentialSyncView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sync_request = OfflineCredentialSyncRequest.model_validate(
            request.data
        )

        users = determine_eligible_users(request.user)

        snapshot = issue_offline_credentials(
            users=users,
            public_key=sync_request.public_key,
        )

        return Response(snapshot.model_dump())
```

`determine_eligible_users()` belongs to the host application.

It is intentionally not part of `django-offline-auth`.

## Credential Failures

User-specific credential problems do not need to fail the entire synchronization batch.

For example:

```text
Mary
    valid supported password
    → credential issued

John
    unusable password
    → failure returned

Peter
    valid supported password
    → credential issued
```

The response may therefore contain both:

```text
credentials[]
failures[]
```

Examples of user-level failures include:

```text
unusable_password
unsupported_password_algorithm
invalid_password_verifier
```

An invalid Android public key or other request-wide cryptographic failure should fail the synchronization request because credentials cannot be securely generated.

## Supported Password Algorithm

Protocol version 1 supports Django:

```text
pbkdf2_sha256
```

The package checks the user's current Django password verifier before issuing a credential.

Unsupported Django password algorithms are not sent to the client.

This prevents the backend from issuing a verifier that the Android implementation cannot validate.

## Cryptography

Protocol version 1 uses:

```text
Password verification:
PBKDF2-HMAC-SHA256

Credential encryption:
AES-256-GCM

AES key protection:
RSA-OAEP-SHA256

Private key storage:
Android Keystore
```

For every credential:

```text
fresh AES-256 key
        ↓
encrypt credential payload with AES-GCM
        ↓
wrap AES key using Android RSA public key
        ↓
return encrypted envelope
```

The Android private key never leaves Android Keystore.

The public key may be sent to Django during credential synchronization and does not need to be persisted by Django.

Different Android installations can therefore request independently encrypted copies of the same user's credential without Django storing device records.

## Public-Key Requirements

The supplied public key must:

```text
be Base64 encoded
contain DER SubjectPublicKeyInfo data
be an RSA public key
meet the configured minimum RSA key size
```

The default minimum RSA key size is:

```text
2048 bits
```

Invalid or unsupported keys are rejected before credentials are returned.

## Configuration

The default offline credential lifetime is 24 hours.

A host Django project can override it:

```python
DJANGO_OFFLINE_AUTH_CREDENTIAL_TTL_SECONDS = 24 * 60 * 60
```

The minimum RSA key size can also be configured:

```python
DJANGO_OFFLINE_AUTH_MIN_RSA_KEY_SIZE = 2048
```

Configuration rules:

```text
credential TTL
    must be an integer
    must be greater than 0

minimum RSA key size
    must be an integer
    must be at least 2048
```

An individual issuance call may also override the configured TTL:

```python
from datetime import timedelta

snapshot = issue_offline_credentials(
    users=eligible_users,
    public_key=public_key,
    ttl=timedelta(hours=6),
)
```

The precedence is:

```text
explicit ttl argument
        ↓
Django setting
        ↓
package default
```

## Offline Credential Policy

Offline credentials:

- are based on the user's current Django password verifier;
- are encrypted before leaving Django;
- are never persisted as plaintext by the package;
- expire after a configurable period;
- use 24 hours by default;
- are refreshed when the application successfully synchronizes online.

If a password changes while a client is offline, the old cached credential may remain usable until the next synchronization or credential expiry.

The new password becomes available for offline authentication after a successful synchronization.

## Synchronization

The host application determines which users should be available offline.

`django-offline-auth` does not know or care how those users were selected.

The synchronization response is treated as the authoritative offline-user snapshot.

Example:

```text
Current Android cache:

Mary
John
Peter


Latest server credentials:

Mary


Android result:

keep/update Mary
remove John
remove Peter
```

The mobile application should therefore remove previously cached credentials that are no longer present in the latest authoritative synchronization result.

User-level entries in `failures` should also be handled appropriately by the host/mobile application because those users were considered for synchronization but could not receive a new credential.

## Account State

Inactive Django users do not receive offline credentials.

```text
user.is_active = False
    → no credential issued
```

Users with no `OfflineAuth` record are also excluded.

Users with:

```text
OfflineAuth.is_enabled = False
```

are excluded.

Because offline authentication must function without connectivity, server-side account changes cannot instantly revoke a credential on a disconnected device.

Changes take effect when:

```text
the device synchronizes again
OR
the cached credential expires
```

## Multiple Users on One Android Installation

A single Android installation may cache credentials for multiple users.

Offline login should:

```text
receive username + password
        ↓
find exactly that username locally
        ↓
load that user's encrypted credential
        ↓
decrypt using Android Keystore
        ↓
verify that user's password
```

The client should not iterate PBKDF2 verification across all cached users.

## Security Rules

- Never put Django password hashes in JWT claims.
- Never return password verifiers as plaintext API data.
- Never persist another plaintext copy of `user.password`.
- Never log passwords, verifiers, AES keys, or private keys.
- Never store Android private keys outside Android Keystore.
- Never trust client-supplied user IDs to decide who receives offline credentials.
- Always use HTTPS.
- Always validate supplied public keys.
- Use a fresh AES key and nonce for every credential issuance.
- Offline authentication must respect credential expiry.
- Sensitive verifier material should exist only transiently in backend memory.
- Decrypted verifier material should remain inside native Android code.

Application-level encryption does not replace TLS.

HTTPS remains mandatory.

## Package Boundary

`django-offline-auth` is responsible for:

```text
OfflineAuth policy
credential generation
credential versioning
protocol definition
credential expiry
password-algorithm validation
public-key validation
AES-GCM encryption
RSA-OAEP key wrapping
user-level issuance failures
```

The host application is responsible for:

```text
which users are eligible
business rules
permissions
authentication
authorization
API integration
when users are enabled or disabled for offline authentication
```

Android is responsible for:

```text
Android Keystore
private-key protection
encrypted local storage
credential decryption
offline password verification
attempt limiting
credential expiry enforcement
authoritative snapshot replacement
removal of stale credentials
```

## Design Principles

The package follows a few important principles.

```text
Host application decides WHO.

django-offline-auth decides HOW credentials are securely issued.

Android decides HOW encrypted credentials are protected and used offline.
```

The Django package intentionally avoids device ownership or enrollment models.

This keeps it reusable across different Django applications and allows multiple Android installations to independently request encrypted credentials without introducing device-specific backend state.

## Protocol Version

Current protocol:

```text
protocol_version = 1
```

Protocol version 1 currently defines:

```text
password algorithm:
pbkdf2_sha256

key wrapping:
RSA-OAEP-256

content encryption:
A256GCM
```

Future protocol changes should increment `protocol_version` when the wire format or cryptographic contract changes.
