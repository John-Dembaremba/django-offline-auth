# django-offline-auth

Reusable Django package for securely issuing offline authentication credentials to mobile applications.

The package is intentionally **user-centric and device-agnostic on the Django side**. It does not store device IDs, device names, IMEI numbers, asset relationships, or Android private keys.

The host Django application decides which users are eligible for offline authentication, while this package securely prepares and encrypts their offline credentials.

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

The backend is user-centric, while Android protects downloaded credentials using an installation-local private key stored in Android Keystore.

## Main Flow

```text
ONLINE

User logs in normally
        ↓
Django returns JWT
        ↓
Host app determines eligible offline users
        ↓
Android sends its public key
        ↓
django-offline-auth reads each user's current Django password verifier
        ↓
Credential payload is encrypted
        ↓
Encrypted credentials are downloaded and stored locally


OFFLINE

User enters username + password
        ↓
Android finds that user's downloaded credential
        ↓
Android Keystore private key decrypts the credential
        ↓
Django password verifier is recovered in native code
        ↓
PBKDF2 verification runs locally
        ↓
Success / Failure
```

## Cryptography

Version 1 uses:

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

The Android private key never leaves Android Keystore.

The public key may be sent to Django during credential synchronization and does not need to be stored by Django.

## Offline Credential Policy

Offline credentials:

- are based on the user's current Django password verifier;
- are encrypted before leaving Django;
- are never stored as plaintext by the package;
- expire after a configurable period, initially 24 hours;
- are refreshed when the application successfully synchronizes online.

If a password changes while a device is offline, the old cached credential may remain valid until the next sync or expiry.

## Synchronization

The host application supplies the users that should be available offline.

For example:

```text
Logged-in User
      ↓
UserProfile
      ↓
Cost Centre
      ↓
Eligible Users
```

`django-offline-auth` does not know about `UserProfile`, `CostCenter`, `Asset`, or other application-specific models.

The server response is treated as the authoritative offline-user snapshot.

If a previously cached user is missing from the latest sync, Android should remove that user's offline credential.

## Security Rules

- Never put Django password hashes in JWT claims.
- Never return password verifiers as plaintext API data.
- Never persist another plaintext copy of `user.password`.
- Never log passwords, verifiers, AES keys, or private keys.
- Never store Android private keys outside Android Keystore.
- Never trust client-supplied user IDs to decide who receives offline credentials.
- Always use HTTPS.
- Always validate supplied public keys.
- Offline authentication must respect credential expiry.

## Package Boundary

`django-offline-auth` is responsible for:

```text
OfflineAuth policy
credential generation
protocol definition
credential expiry
public-key validation
AES-GCM encryption
RSA-OAEP key wrapping
```

The host application is responsible for:

```text
which users are eligible
business rules
cost centres
assets
permissions
API integration
```

Android is responsible for:

```text
Android Keystore
encrypted local storage
credential decryption
offline password verification
attempt limiting
snapshot replacement
```
