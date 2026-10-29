from django.contrib import admin

from django_offline_auth.application.services.manage_offline_auth import (
    disable_offline_auth,
    enable_offline_auth,
    rotate_offline_credentials,
)
from django_offline_auth.models import OfflineAuth


@admin.register(OfflineAuth)
class OfflineAuthAdmin(admin.ModelAdmin):
    """Manage offline authentication settings."""

    list_display = (
        "user",
        "is_enabled",
        "credential_version",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "is_enabled",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "is_enabled",
        "credential_version",
        "created_at",
        "updated_at",
    )

    ordering = ("user__username",)

    actions = (
        "enable_selected",
        "disable_selected",
        "rotate_selected",
    )

    @admin.action(
        description="Enable offline authentication",
    )
    def enable_selected(self, request, queryset):
        for offline_auth in queryset.select_related("user"):
            enable_offline_auth(offline_auth.user)

    @admin.action(
        description="Disable offline authentication",
    )
    def disable_selected(self, request, queryset):
        for offline_auth in queryset.select_related("user"):
            disable_offline_auth(offline_auth.user)

    @admin.action(
        description="Rotate offline credentials",
    )
    def rotate_selected(self, request, queryset):
        for offline_auth in queryset.select_related("user"):
            rotate_offline_credentials(offline_auth.user)
