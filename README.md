# django-offline-auth

Reusable offline authentication support for Django applications.

## Purpose

`django-offline-auth` provides the server-side building blocks required to
issue secure offline authentication credentials for mobile applications.

The package is intentionally device-agnostic on the Django side.

It does not store:

- device IDs
- device names
- IMEI numbers
- asset relationships
- Android private keys

The host Django application determines which users are eligible for offline
authentication.

The package is responsible for securely packaging and encrypting offline
credentials.

## Architecture

The backend is user-centric.

The Android client protects downloaded credentials using an installation-local
private key stored in Android Keystore.

## Status

Early development.

Current protocol version: `1`.
