# django-offline-auth

Reusable Django package for securely issuing offline authentication credentials to mobile applications.

The Django side is intentionally **user-centric and device-agnostic**.

It does not store device IDs, IMEI numbers, device ownership, Android private keys, or extra copies of user password verifiers.

The host application decides **who** can authenticate offline. `django-offline-auth` handles **how** their credentials are securely issued.

## Architecture

```text
Host Django Application
        │
        │ selects eligible users
        ▼
django-offline-auth
        │
        │ encrypts offline credentials
        ▼
Android Application
        │
        │ protects private key with Android Keystore
        ▼
Offline Authentication
```

## Installation

```bash
pip install django-offline-auth
```

Add it to Django:

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

## Public API

```python
from django_offline_auth.application import (
    disable_offline_auth,
    enable_offline_auth,
    is_enabled_offline_auth,
    issue_offline_credentials,
    rotate_offline_credentials,
)
```

Enable offline authentication:

```python
enable_offline_auth(user)
```

Check whether it is enabled:

```python
if is_enabled_offline_auth(user):
    print("Offline authentication is enabled")
```

Disable it:

```python
disable_offline_auth(user)
```

Rotate the user's offline credential state:

```python
rotate_offline_credentials(user)
```

`credential_version` is incremented when credentials are explicitly rotated or when offline authentication is disabled and later re-enabled.

## Issuing Offline Credentials

The host application decides which users should be available offline:

```python
snapshot = issue_offline_credentials(
    users=eligible_users,
    public_key=android_public_key,
)
```

The package:

1. checks that each user is active and enabled for offline authentication;
2. validates the user's Django password verifier;
3. builds an offline credential payload;
4. encrypts the payload with AES-256-GCM;
5. wraps the AES key using the Android RSA public key;
6. returns an encrypted synchronization snapshot.

## Synchronization Request

The mobile application sends its RSA public key:

```json
{
  "public_key": "MIIBIjANBgkqh..."
}
```

The host application must decide which users are eligible. Clients should never be allowed to submit arbitrary user IDs to determine who receives offline credentials.

## Synchronization Response

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

A problem with one user does not have to fail the entire synchronization batch.

Possible user-level failures include:

```text
unusable_password
unsupported_password_algorithm
invalid_password_verifier
```

## Offline Flow

```text
User enters username + password
        ↓
Android finds that user's encrypted credential
        ↓
Android Keystore private key unwraps the AES key
        ↓
AES-GCM decrypts the credential payload
        ↓
PBKDF2 verifies the password
        ↓
Success / Failure
```

A single Android installation may cache credentials for multiple users.

The client should look up the entered username first and verify only that user's credential.

## Cryptography

Protocol version 1 uses:

```text
Password verifier:
pbkdf2_sha256

Content encryption:
AES-256-GCM

AES key wrapping:
RSA-OAEP-SHA256

Private key storage:
Android Keystore
```

The Android private key must never leave Android Keystore.

The public key may be sent to Django during synchronization and does not need to be stored by the backend.

## Credential Policy

Offline credentials:

- use the user's current Django password verifier;
- are encrypted before leaving Django;
- are never returned as plaintext API data;
- expire after a configurable period;
- use a default lifetime of 24 hours;
- are refreshed during successful synchronization.

If a password changes while a device is offline, the previous cached credential may remain valid until the next synchronization or credential expiry.

## Authoritative Snapshot

The synchronization result is treated as the authoritative set of offline credentials.

If Android previously has:

```text
Mary
John
Peter
```

and the latest successful synchronization returns only:

```text
Mary
```

Android should keep/update Mary and remove John and Peter.

## Configuration

Default credential lifetime:

```python
DJANGO_OFFLINE_AUTH_CREDENTIAL_TTL_SECONDS = 24 * 60 * 60
```

Minimum RSA key size:

```python
DJANGO_OFFLINE_AUTH_MIN_RSA_KEY_SIZE = 2048
```

An individual request may override the default TTL:

```python
from datetime import timedelta

snapshot = issue_offline_credentials(
    users=eligible_users,
    public_key=public_key,
    ttl=timedelta(hours=6),
)
```

## Security Rules

- Never include Django password hashes in JWTs.
- Never expose password verifiers as plaintext API data.
- Never log passwords, verifiers, AES keys, or private keys.
- Never persist another plaintext copy of `user.password`.
- Never store Android private keys outside Android Keystore.
- Always validate supplied public keys.
- Always use HTTPS.
- Use a fresh AES key and nonce for every credential.
- Enforce credential expiry on the mobile client.
- Keep decrypted verifier material inside native Android code.

Application-level encryption does not replace TLS.

## Responsibilities

### Host Django Application

Responsible for:

```text
authentication
authorization
business rules
selecting eligible users
API integration
```

### django-offline-auth

Responsible for:

```text
OfflineAuth state
credential generation
credential versioning
expiry
password verifier validation
AES-GCM encryption
RSA-OAEP key wrapping
synchronization response
```

### Android Application

Responsible for:

```text
Android Keystore
private-key protection
encrypted local storage
credential decryption
offline password verification
expiry enforcement
attempt limiting
authoritative snapshot replacement
```

## Protocol Version

Current protocol:

```text
protocol_version = 1
```

Protocol v1 supports:

```text
Password algorithm: pbkdf2_sha256
Key wrapping:       RSA-OAEP-256
Encryption:         A256GCM
```

Breaking changes to the wire format or cryptographic contract should increment `protocol_version`.
