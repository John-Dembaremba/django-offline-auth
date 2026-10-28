from datetime import timedelta

import pytest
from django.test import override_settings

from django_offline_auth.conf import (
    get_credential_ttl,
    get_min_rsa_key_size,
)


def test_default_credential_ttl():
    assert get_credential_ttl() == timedelta(hours=24)


@override_settings(
    DJANGO_OFFLINE_AUTH_CREDENTIAL_TTL_SECONDS=3600,
)
def test_custom_credential_ttl():
    assert get_credential_ttl() == timedelta(hours=1)


def test_default_min_rsa_key_size():
    assert get_min_rsa_key_size() == 2048


@override_settings(
    DJANGO_OFFLINE_AUTH_MIN_RSA_KEY_SIZE=3072,
)
def test_custom_min_rsa_key_size():
    assert get_min_rsa_key_size() == 3072


@override_settings(
    DJANGO_OFFLINE_AUTH_CREDENTIAL_TTL_SECONDS="3600",
)
def test_credential_ttl_must_be_integer():
    with pytest.raises(TypeError):
        get_credential_ttl()


@override_settings(
    DJANGO_OFFLINE_AUTH_CREDENTIAL_TTL_SECONDS=-3600,
)
def test_credential_ttl_must_be_positive():
    with pytest.raises(ValueError):
        get_credential_ttl()


@override_settings(
    DJANGO_OFFLINE_AUTH_MIN_RSA_KEY_SIZE="3600",
)
def test_credential_rsa_must_be_integer():
    with pytest.raises(TypeError):
        get_min_rsa_key_size()


@override_settings(
    DJANGO_OFFLINE_AUTH_MIN_RSA_KEY_SIZE=1024,
)
def test_credential_rsa_must_be_gt_2048():
    with pytest.raises(ValueError):
        get_min_rsa_key_size()
