import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django_offline_auth.models import OfflineAuth

pytestmark = pytest.mark.django_db


def test_django_offline_auth_is_installed():
    app_config = apps.get_app_config("django_offline_auth")

    assert app_config.name == "django_offline_auth"


def test_offline_auth_can_be_created_for_user():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
        password="secret123",
    )

    offline_auth = OfflineAuth.objects.create(
        user=user,
    )

    assert offline_auth.user == user
    assert offline_auth.is_enabled is True
    assert offline_auth.credential_version == 1


def test_user_can_only_have_one_offline_auth_record():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
        password="secret123",
    )

    OfflineAuth.objects.create(
        user=user,
    )

    with pytest.raises(IntegrityError):
        OfflineAuth.objects.create(
            user=user,
        )


def test_offline_auth_is_deleted_when_user_is_deleted():
    User = get_user_model()

    user = User.objects.create_user(
        username="john",
        password="secret123",
    )

    offline_auth = OfflineAuth.objects.create(
        user=user,
    )

    offline_auth_id = offline_auth.pk

    user.delete()

    assert not OfflineAuth.objects.filter(
        pk=offline_auth_id,
    ).exists()
