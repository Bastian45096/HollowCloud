from django.contrib import admin

from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "title",
        "notification_type",
        "is_read",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "is_read",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__username",
        "title",
        "message",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "read_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (
            "Información General",
            {
                "fields": (
                    "id",
                    "user",
                    "title",
                    "message",
                    "notification_type",
                )
            },
        ),
        (
            "Estado",
            {
                "fields": (
                    "is_read",
                    "read_at",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "email_enabled",
        "in_app_enabled",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__username",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("user__email",)