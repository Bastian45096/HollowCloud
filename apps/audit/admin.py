from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "action",
        "entity_type",
        "entity_id",
        "ip_address",
        "created_at",
    )

    list_filter = (
        "action",
        "entity_type",
        "created_at",
    )

    search_fields = (
        "user__email",
        "action",
        "entity_type",
        "entity_id",
    )

    readonly_fields = (
        "id",
        "user",
        "action",
        "entity_type",
        "entity_id",
        "metadata",
        "ip_address",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (
            "Información General",
            {
                "fields": (
                    "id",
                    "user",
                    "action",
                    "entity_type",
                    "entity_id",
                )
            },
        ),
        (
            "Detalles Técnicos",
            {
                "fields": (
                    "ip_address",
                    "metadata",
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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False