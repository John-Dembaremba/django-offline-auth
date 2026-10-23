from django.apps import apps


def test_django_offline_auth_is_installed():
    app_config = apps.get_app_config("django_offline_auth")

    assert app_config.name == "django_offline_auth"