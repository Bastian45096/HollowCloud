from django.contrib import admin

from .models import FileShare, FileVersion, Folder, StoredFile


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "workspace",
        "parent",
        "created_at",
    )

    search_fields = (
        "name",
        "workspace__name",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("workspace", "name")


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "workspace",
        "uploaded_by",
        "mime_type",
        "size",
        "current_version",
        "created_at",
    )

    search_fields = (
        "name",
        "workspace__name",
        "uploaded_by__email",
        "uploaded_by__username",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)


@admin.register(FileVersion)
class FileVersionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "stored_file",
        "version_number",
        "uploaded_by",
        "size",
        "created_at",
    )

    search_fields = (
        "stored_file__name",
        "uploaded_by__email",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)


@admin.register(FileShare)
class FileShareAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "stored_file",
        "shared_with",
        "can_edit",
        "created_at",
    )

    list_filter = (
        "can_edit",
        "created_at",
    )

    search_fields = (
        "stored_file__name",
        "shared_with__email",
        "shared_with__username",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)