from django.urls import include, path


urlpatterns = [
    path(
        "offline-auth/",
        include("django_offline_auth.urls"),
    ),
]