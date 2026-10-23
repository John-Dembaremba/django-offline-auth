Your current README already establishes the two most important principles: the package is intentionally **device-agnostic on Django**, and the host application decides which users are eligible for offline authentication. README(5) It also states that Android protects downloaded credentials with an installation-local private key stored in Android Keystore. README(5)

I’d expand it into this so a new developer can understand the problem, boundaries, security rules, and full online/offline flow before touching the code.

# django-offline-auth

Reusable offline authentication support for Django applications.

`django-offline-auth` provides server-side building blocks for securely issuing offline authentication credentials to mobile applications.

The package is designed primarily for systems where:

- users normally authenticate against Django while online;
- a mobile application may later lose network connectivity;
- multiple users may need to authenticate on the same mobile installation while offline;
- the mobile application already downloads user/profile information for offline use;
- Django password verifiers must not be exposed inside JWT tokens or stored unprotected on the mobile device.

---

## 1. Problem

Django stores passwords as encoded password verifiers similar to:

```text
pbkdf2_sha256$1000000$salt$hash
```

A mobile application can technically use that encoded value to verify a password offline by reproducing Django's PBKDF2 calculation locally.

A previous implementation placed the Django password verifier directly inside JWT claims so that the mobile application could download it and use it for offline authentication.

That creates a serious security issue.

JWT payloads are normally encoded, not encrypted.

An attacker who obtains a JWT can therefore decode the payload and recover the password verifier.

The attacker can then perform password guessing offline without communicating with the Django server.

The purpose of this package is to preserve offline authentication while removing Django password verifiers from JWTs and preventing them from being stored in plaintext on Android.

---

# 2. Core Design

The architecture separates three responsibilities.

```text
Host Django Application
        │
        │ decides WHO may authenticate offline
        ▼
django-offline-auth
        │
        │ securely prepares offline credentials
        ▼
Android Offline Auth Library
        │
        │ stores and verifies credentials locally
        ▼
Offline Authentication
```

The host application owns business rules.

`django-offline-auth` owns credential generation and cryptographic packaging.

The Android library owns local key protection, credential storage, decryption, and password verification.

---

# 3. Fundamental Architecture Rule

The Django backend is:

```text
USER-CENTRIC
```

The Android implementation is:

```text
INSTALLATION-PROTECTED
```

The Django package does not maintain a device registry.

Android still uses installation-local cryptographic keys to protect downloaded credentials.

These are separate concepts.

---

# 4. What Django Stores

The package may maintain offline-authentication policy associated with a Django user.

Conceptually:

```text
User
 │
 ├── Django password
 │
 └── OfflineAuth
      ├── is_enabled
      ├── credential_version
      ├── created_at
      └── updated_at
```

The Django `User.password` field remains the source of truth for the user's password verifier.

The package must not create another permanent plaintext copy of that verifier.

---

# 5. What Django Does Not Store

`django-offline-auth` is intentionally device-agnostic.

It does not store:

- device IDs;
- device names;
- IMEI numbers;
- Android IDs;
- asset IDs;
- asset relationships;
- device ownership information;
- device assignments;
- cost centres;
- Android private keys;
- Android public keys permanently;
- plaintext offline password credentials.

The package must not depend directly on application-specific models such as:

```python
Asset
UserProfile
CostCenter
Region
Department
```

Those belong to the host application.

---

# 6. Host Application Responsibility

The host Django application determines which users should be available for offline authentication.

For example, a host application may have this business rule:

```text
Logged-in User
      ↓
UserProfile
      ↓
Cost Centre
      ↓
Users belonging to that Cost Centre
      ↓
Eligible Offline Users
```

For example:

```text
John logs in online

John
 ↓
Cost Centre CC001
 ↓
John
Mary
Peter
Susan
```

The host application may then pass:

```text
John
Mary
Peter
Susan
```

to `django-offline-auth`.

The package does not need to know why those users were selected.

The rule is:

```text
Host application decides WHO.

django-offline-auth decides HOW.
```

---

# 7. OfflineAuth Policy

The package may contain a small per-user model such as:

```python
OfflineAuth
```

Its responsibility is to describe whether a user is eligible for offline authentication.

Conceptually:

```text
User
 │
 └── OfflineAuth
      ├── is_enabled
      └── credential_version
```

The model must not contain:

```text
password_hash
device_id
device_name
public_key
private_key
encrypted_password
asset_id
```

The Django password verifier already exists in:

```python
user.password
```

and should only be accessed temporarily during credential generation.

---

# 8. Normal Online Authentication

Normal Django authentication remains unchanged.

The mobile application sends:

```text
username
password
```

to the normal Django authentication endpoint.

Django authenticates the user.

The application receives a normal access token / refresh token.

The JWT must contain only identity and authorization information.

For example:

```json
{
  "user_id": 42,
  "username": "john",
  "exp": 1234567890
}
```

JWTs must never contain:

```json
{
  "password": "pbkdf2_sha256$..."
}
```

or:

```json
{
  "password_hash": "..."
}
```

or any equivalent Django password verifier.

---

# 9. Android Cryptographic Identity

The Android application creates an asymmetric key pair using Android Keystore.

Conceptually:

```text
Android Keystore

Private Key
Public Key
```

The private key:

- remains inside Android Keystore;
- must not be exported;
- must not be stored in SQLite;
- must not be stored in AsyncStorage;
- must not be passed to React Native JavaScript;
- must not be sent to Django.

The public key:

- is not secret;
- may be exported;
- is sent to Django during offline credential synchronization;
- does not need to be permanently stored by Django.

---

# 10. No Django Device Registration

The Django package deliberately does not create records such as:

```text
OfflineDevice
DeviceRegistration
RegisteredPhone
AssetDevice
```

Instead, the mobile application sends its public key with the synchronization request.

Example conceptually:

```json
{
  "public_key": "MIIBIjANBgkqh..."
}
```

Django uses that key for the current request and may discard it afterward.

The backend does not need to know:

```text
which phone this is
who owns the phone
whether it is an asset
the device name
the IMEI
```

---

# 11. Offline Credential Synchronization

After a successful online login:

```text
Online login succeeds
        ↓
Android obtains installation public key
        ↓
Offline credential sync endpoint is called
        ↓
Host application determines eligible users
        ↓
django-offline-auth prepares credentials
        ↓
Credentials are encrypted for the Android installation
        ↓
Android stores the encrypted credentials locally
```

This sync operation is separate from JWT issuance.

---

# 12. Credential Source

For each eligible user, the package obtains the current Django verifier from:

```python
user.password
```

For example:

```text
pbkdf2_sha256$1000000$salt$hash
```

The entire Django encoded password value is treated as the verifier.

The package should not extract only:

```text
$hash
```

because the Android verifier also needs:

```text
algorithm
iterations
salt
hash
```

to reproduce Django's password verification process.

---

# 13. Credential Payload

Before encryption, the package creates an internal payload similar to:

```json
{
  "protocol_version": 1,
  "user_id": "42",
  "username": "mary",
  "verifier": "pbkdf2_sha256$1000000$salt$hash",
  "issued_at": "2026-10-23T06:00:00Z",
  "expires_at": "2026-10-24T06:00:00Z",
  "credential_version": 1
}
```

This plaintext payload:

- exists only temporarily in memory;
- must never be logged;
- must never be persisted in the package database;
- must never be returned directly to the client.

---

# 14. Credential Expiration

Offline credentials are initially designed to expire after:

```text
24 hours
```

Example:

```text
issued_at:
23 October 2026 08:00

expires_at:
24 October 2026 08:00
```

After expiry, the Android application must reject offline authentication until a successful online synchronization occurs again.

The 24-hour period should be configurable.

The host application may later choose a different policy.

---

# 15. Why Expiration Is Important

An offline device cannot know immediately about server-side changes.

For example:

```text
08:00
Device downloads Mary's credential.

12:00
Mary changes her password somewhere else.

13:00
Device remains offline.
```

The offline device still contains Mary's old verifier.

Therefore:

```text
old password → may still work offline
new password → may not work offline yet
```

until the device reconnects and synchronizes.

Expiration limits how long stale credentials remain usable.

---

# 16. Password Change Behaviour

Django's `User.password` remains the source of truth.

Suppose:

```text
old password verifier = HASH-A
```

and the device synchronizes it.

Mary later changes her password.

Django now stores:

```text
new password verifier = HASH-B
```

Nothing needs to be manually changed in the `OfflineAuth` record.

During the next sync:

```text
user.password
      ↓
HASH-B
      ↓
new encrypted offline credential
```

The Android client replaces the old credential.

After synchronization:

```text
old password → fails
new password → succeeds
```

---

# 17. User Removal Behaviour

The synchronization response must represent an authoritative snapshot of users currently allowed offline.

Suppose Android currently stores:

```text
John
Mary
Peter
Susan
```

The next server synchronization returns:

```text
John
Peter
Susan
```

Mary is missing.

Android must therefore remove Mary's local offline credential.

Synchronization must not behave as:

```text
add whatever the server sends
```

It must behave as:

```text
make local offline users match the server snapshot
```

This handles:

- user transfers;
- cost-centre changes;
- account deactivation;
- team membership changes;
- new users;
- removed users.

---

# 18. Envelope Encryption

The offline verifier must not be stored or transported as plaintext.

The package uses hybrid / envelope encryption.

The credential payload is encrypted with:

```text
AES-256-GCM
```

A fresh random AES key is generated for the credential.

That AES key is then encrypted using the Android application's public key with:

```text
RSA-OAEP-SHA256
```

Conceptually:

```text
Offline Credential JSON
        │
        ▼
Random AES-256 Key
        │
        ▼
AES-GCM Encryption
        │
        ▼
Ciphertext
```

Meanwhile:

```text
AES Key
   │
   ▼
Android RSA Public Key
   │
   ▼
RSA-OAEP-SHA256
   │
   ▼
Encrypted AES Key
```

The server then returns:

```text
encrypted AES key
nonce
ciphertext
```

---

# 19. Why AES and RSA Are Both Used

RSA is not used to encrypt the entire credential payload.

RSA is used only to protect the AES key.

AES-GCM encrypts the actual payload.

The responsibilities are:

```text
AES-GCM
    encrypt credential payload
    detect tampering

RSA-OAEP
    safely deliver AES key

Android Keystore
    protect RSA private key
```

---

# 20. Example Encrypted Credential

The mobile application may receive:

```json
{
  "lookup": {
    "user_id": "42",
    "username": "mary"
  },
  "envelope": {
    "key_algorithm": "RSA-OAEP-256",
    "content_algorithm": "A256GCM",
    "encrypted_key": "...",
    "nonce": "...",
    "ciphertext": "..."
  }
}
```

The Django password verifier does not appear in plaintext.

---

# 21. Android Local Storage

The Android application may store locally:

```text
user_id
username
profile information
encrypted_key
nonce
ciphertext
sync metadata
```

It must not persist:

```text
plaintext Django verifier
plaintext AES key
RSA private key
typed passwords
```

The private RSA key remains in Android Keystore.

---

# 22. Offline Login Flow

Suppose the device is offline.

Mary enters:

```text
username: mary
password: ********
```

The Android application performs:

```text
username
    ↓
find Mary's local downloaded profile
    ↓
find Mary's encrypted offline credential
    ↓
load encrypted AES key
    ↓
Android Keystore private RSA key
    ↓
RSA-OAEP decrypt AES key
    ↓
AES-GCM decrypt credential payload
    ↓
validate credential
    ↓
extract Django encoded verifier
    ↓
PBKDF2 password verification
    ↓
success / failure
```

---

# 23. Offline Password Verification

A Django PBKDF2 verifier contains:

```text
algorithm
iterations
salt
hash
```

Example:

```text
pbkdf2_sha256$1000000$salt$hash
```

Android splits the value.

Then:

```text
entered password
      +
salt
      +
iteration count
      ↓
PBKDF2-HMAC-SHA256
      ↓
generated hash
```

The generated hash is compared against Django's expected hash.

If they match:

```text
authentication succeeds
```

Otherwise:

```text
authentication fails
```

---

# 24. Multiple Users on One Android Installation

Multi-user offline authentication is a first-class requirement.

One Android installation may store encrypted credentials for many users.

Example:

```text
Android Installation

├── John
│   └── encrypted offline credential
│
├── Mary
│   └── encrypted offline credential
│
├── Peter
│   └── encrypted offline credential
│
└── Susan
    └── encrypted offline credential
```

During offline login, the application first selects the user by username.

It must not run password verification against every cached user.

Correct:

```text
username
   ↓
lookup one user
   ↓
decrypt one credential
   ↓
run PBKDF2 once
```

Incorrect:

```text
password
   ↓
loop through every user
   ↓
run PBKDF2 repeatedly
```

---

# 25. Generic Login Failure

Offline login should not reveal whether a username exists locally.

The UI should preferably return:

```text
INVALID_CREDENTIALS
```

for:

```text
unknown username
wrong password
```

rather than exposing:

```text
USER_NOT_FOUND
```

This reduces username enumeration.

Credential expiration may be reported separately because the user needs to know that network reconnection is required.

---

# 26. Android Keystore Rules

The Android private key must:

- be generated using Android Keystore;
- never leave Android Keystore;
- never be serialized;
- never be stored in SQLite;
- never be sent to Django;
- never be passed through the React Native bridge.

The Android public key may:

- be exported;
- be Base64 encoded;
- be sent to Django for credential synchronization.

---

# 27. React Native Boundary

Sensitive cryptographic operations should remain inside the native Android package.

React Native should not receive:

```text
Django verifier
AES key
RSA private key
salt
hash
```

React Native should use a small API such as:

```text
OfflineAuth.sync()

OfflineAuth.verify(
    username,
    password
)
```

and receive results similar to:

```json
{
  "success": true
}
```

or:

```json
{
  "success": false,
  "reason": "INVALID_CREDENTIALS"
}
```

---

# 28. Cryptographic Responsibilities

Each cryptographic mechanism solves a different problem.

## PBKDF2

Purpose:

```text
Verify whether the entered password is correct.
```

## AES-256-GCM

Purpose:

```text
Encrypt the offline credential efficiently and detect tampering.
```

## RSA-OAEP-SHA256

Purpose:

```text
Securely transport the temporary AES key to the Android installation.
```

## Android Keystore

Purpose:

```text
Protect the Android RSA private key.
```

## HTTPS/TLS

Purpose:

```text
Protect the entire online communication channel and authenticate the server.
```

Application-level encryption does not replace HTTPS.

---

# 29. Protocol Versioning

The protocol must always contain an explicit version.

Current version:

```text
1
```

Example:

```json
{
  "protocol_version": 1
}
```

This allows future versions to use different:

- algorithms;
- payload structures;
- key mechanisms;
- password verifier types.

Android should reject unsupported protocol versions safely.

---

# 30. Algorithm Identifiers

Protocol algorithm names must be explicit.

Version 1 currently targets:

```text
Key wrapping:
RSA-OAEP-256

Content encryption:
A256GCM

Offline password verification:
pbkdf2_sha256
```

Avoid ambiguous identifiers such as:

```text
RSA
AES
```

because they do not describe padding, digest, mode, or key size.

---

# 31. Current Password Algorithm Support

The initial Android implementation supports:

```text
pbkdf2_sha256
```

If Django uses another password hasher for a user, version 1 must reject it rather than silently attempting incorrect verification.

Future protocol/library versions may add support for:

- Argon2;
- scrypt;
- bcrypt;
- additional Django-supported password hashers.

---

# 32. Security Rules

The following rules are mandatory.

### Never place a Django password verifier in a JWT.

Incorrect:

```json
{
  "password": "pbkdf2_sha256$..."
}
```

### Never return the verifier as plaintext from an API.

### Never persist a second plaintext copy of `user.password`.

### Never log:

```text
user.password
typed password
decrypted verifier
AES key
RSA private key
```

### Never store the Android private key outside Android Keystore.

### Never trust user IDs supplied by the mobile client when deciding which users receive credentials.

The host application must determine eligible users server-side.

### Always use HTTPS.

### Always validate client-supplied public keys.

### Always enforce offline credential expiration.

---

# 33. Public Key Validation

Public keys supplied by Android must be validated.

The package should reject:

- malformed Base64;
- malformed DER;
- non-RSA keys;
- insufficient RSA key sizes;
- unsupported key formats;
- unexpectedly large input.

The initial protocol should require at least:

```text
RSA 2048-bit
```

with Android preferably generating:

```text
RSA 3072-bit
```

where appropriate.

---

# 34. Credential Synchronization Must Be Authenticated

Offline credentials must only be issued after normal authenticated online access.

The synchronization endpoint must require an authenticated Django user.

Conceptually:

```text
normal login
    ↓
JWT/access token
    ↓
authenticated offline sync request
```

The package must not expose anonymous password-verifier synchronization.

---

# 35. Client Must Not Choose Arbitrary Users

The mobile client must not send:

```json
{
  "users": [1, 2, 3, 9999]
}
```

and cause the backend to return credentials for those IDs.

Instead:

```text
Authenticated user
        ↓
Host application business rules
        ↓
Server determines eligible users
        ↓
Package issues only those credentials
```

This prevents one user from requesting offline verifiers for arbitrary accounts.

---

# 36. Offline Authentication and Password Changes

Offline systems necessarily operate on a snapshot.

If a password changes while the mobile device is offline, the old cached verifier may remain valid until:

```text
the device synchronizes
```

or:

```text
the credential expires
```

whichever happens first.

This is an expected limitation of offline authentication.

---

# 37. Device Loss and Revocation Trade-off

The backend deliberately does not maintain device identities.

Therefore it cannot remotely revoke one specific Android installation.

If an installation is lost while completely offline, its cached credentials may remain usable until their configured expiry time.

The initial mitigation is:

```text
short credential lifetime
+
Android Keystore
+
encrypted local storage
+
OS/device security
```

If targeted remote device revocation becomes a future requirement, the architecture would need to introduce an enrollment/device identity concept.

That is intentionally outside version 1.

---

# 38. Application Reinstallation

If the Android application is reinstalled and its previous Keystore key becomes unavailable:

```text
old encrypted credentials
    ↓
cannot be decrypted
```

The application should:

```text
clear old cached credentials
require online authentication
generate a new Keystore key pair
download fresh offline credentials
```

It must never fall back to plaintext verifier storage.

---

# 39. Package Boundary

`django-offline-auth` should contain reusable mechanisms such as:

```text
OfflineAuth policy
credential provider
credential payload generation
protocol definitions
public-key validation
AES-GCM encryption
RSA-OAEP key wrapping
credential expiration
```

It should not contain application business logic such as:

```text
CostCenter
AssetRegister
UserProfile rules
department membership
regional authorization
```

---

# 40. Suggested Package Structure

```text
django-offline-auth/
├── pyproject.toml
├── README.md
├── LICENCE
│
├── src/
│   └── django_offline_auth/
│       ├── __init__.py
│       ├── apps.py
│       ├── admin.py
│       ├── models.py
│       ├── urls.py
│       ├── exceptions.py
│       │
│       ├── application/
│       │   ├── interfaces/
│       │   │   ├── credential_provider.py
│       │   │   └── envelope_encryptor.py
│       │   │
│       │   └── services/
│       │       └── issue_credentials.py
│       │
│       ├── infrastructure/
│       │   └── crypto/
│       │       └── envelope.py
│       │
│       ├── protocol/
│       │   ├── constants.py
│       │   └── payloads.py
│       │
│       └── migrations/
│
└── tests/
    ├── unit/
    ├── integration/
    └── security/
```

---

# 41. Dependency Direction

The intended dependency direction is:

```text
Host Application
       │
       ▼
django-offline-auth
       │
       ├── application
       ├── protocol
       └── infrastructure
```

Never:

```text
django-offline-auth
       │
       ▼
Host Application Models
```

The reusable package must never import BE-specific models.

---

# 42. Planned Backend Flow

The final backend flow should resemble:

```text
Authenticated online user
        ↓
Host application resolves eligible offline users
        ↓
django-offline-auth receives users + Android public key
        ↓
Check OfflineAuth eligibility
        ↓
Read current Django verifier
        ↓
Create credential payload
        ↓
Apply expiry
        ↓
Generate random AES-256 key
        ↓
Encrypt payload using AES-GCM
        ↓
Encrypt AES key using RSA-OAEP-SHA256
        ↓
Return encrypted authoritative snapshot
```

---

# 43. Planned Android Flow

The final Android flow should resemble:

```text
Application installation
        ↓
Generate RSA key pair in Android Keystore
        ↓
Export public key
        ↓
Successful online login
        ↓
Send public key during offline sync
        ↓
Receive encrypted users/credentials
        ↓
Store encrypted credentials locally
```

Then offline:

```text
username + password
        ↓
Find downloaded user
        ↓
Load encrypted credential
        ↓
Use Keystore private key to unwrap AES key
        ↓
AES-GCM decrypt credential
        ↓
Check protocol + expiry + username
        ↓
Run Django-compatible PBKDF2 verification
        ↓
Return authenticated / rejected
```

---

# 44. Current Development Status

Current protocol version:

```text
1
```

Current development stage:

```text
Package skeleton created.
Django application loads successfully.
Initial test environment configured.
```

Planned implementation sequence:

```text
1. OfflineAuth model
2. CredentialProvider interface
3. Django password verifier provider
4. Protocol payload objects
5. Public-key validation
6. AES-256-GCM envelope encryption
7. RSA-OAEP-SHA256 key wrapping
8. Credential issuing service
9. Unit/security tests
10. Host Django integration
11. Android/Kotlin package
12. React Native bridge
```

---

# 45. Design Summary

The design can be summarized with four rules:

```text
JWT is for online authentication.

Offline credentials are separate from JWT.

Django is user-centric and device-agnostic.

Android Keystore protects credentials on the mobile installation.
```

The complete architecture is:

```text
                   DJANGO

User.password
     │
     ├──────────────► Normal online authentication
     │                       │
     │                       ▼
     │                      JWT
     │              no password verifier
     │
     ▼
django-offline-auth
     │
     ├── build offline credential
     ├── 24-hour expiry
     ├── AES-GCM encrypt
     └── RSA-OAEP wrap AES key
                 │
                 ▼
          Android application
                 │
                 ▼
        encrypted local storage


--------------------------------------------


                  OFFLINE

username + password
        │
        ▼
downloaded local user
        │
        ▼
encrypted credential
        │
        ▼
Android Keystore
        │
        ▼
decrypt credential
        │
        ▼
Django PBKDF2 verifier
        │
        ▼
verify entered password
        │
     ┌──┴──┐
     ▼     ▼
 success  failure
```

The primary goal is to preserve practical multi-user offline authentication without exposing Django password verifiers through JWTs or plaintext mobile storage.

This is the version I’d keep as the architectural source of truth while we implement the package. As we add features, we should update the README only when an actual design decision changes, rather than letting the code and architecture documentation drift apart.
