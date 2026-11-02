import pytest
from django.contrib.auth import get_user_model

from django_offline_auth.application import (
    disable_offline_auth,
    enable_offline_auth,
    rotate_offline_credentials,
)
from django_offline_auth.application.services.manage_offline_auth import (
    is_enabled_offline_auth,
)
from django_offline_auth.models import OfflineAuth

pytestmark = pytest.mark.django_db


def test_enable_offline_auth_creates_record():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
        password="secret123",
    )

    offline_auth = enable_offline_auth(user)

    assert offline_auth.user == user
    assert offline_auth.is_enabled is True
    assert OfflineAuth.objects.filter(
        user=user,
    ).exists()


def test_enable_offline_auth_reenables_disabled_record():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=False,
    )

    offline_auth = enable_offline_auth(user)

    assert offline_auth.is_enabled is True


def test_disable_offline_auth_disables_user():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
    )

    offline_auth = disable_offline_auth(user)

    assert offline_auth.is_enabled is False


def test_reenable_increments_credential_version():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=False,
        credential_version=1,
    )

    offline_auth = enable_offline_auth(user)

    assert offline_auth.is_enabled is True
    assert offline_auth.credential_version == 2


def test_enable_does_not_increment_when_already_enabled():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        is_enabled=True,
        credential_version=1,
    )

    offline_auth = enable_offline_auth(user)

    assert offline_auth.credential_version == 1


def test_rotate_offline_credentials_increments_version():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
        credential_version=1,
    )

    offline_auth = rotate_offline_credentials(user)

    assert offline_auth.credential_version == 2


def test_is_enabled_offline_auth_returns_false_when_not_created():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
        password="secret123",
    )

    assert is_enabled_offline_auth(user) is False


def test_is_enabled_offline_auth_returns_true_when_enabled():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
        password="secret123",
    )

    enable_offline_auth(user)

    assert is_enabled_offline_auth(user) is True


def test_is_enabled_offline_auth_returns_false_when_disabled():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
        password="secret123",
    )

    enable_offline_auth(user)
    disable_offline_auth(user)

    assert is_enabled_offline_auth(user) is False
