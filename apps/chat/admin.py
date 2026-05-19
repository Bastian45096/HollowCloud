from django.contrib import admin

from .models import (
    Channel,
    Message,
    MessageAttachment,
    Workspace,
    WorkspaceMember,
)


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "owner",
        "created_at",
    )

    search_fields = (
        "name",
        "slug",
        "owner__email",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("name",)


@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "workspace",
        "user",
        "role",
        "created_at",
    )

    list_filter = (
        "role",
        "created_at",
    )

    search_fields = (
        "workspace__name",
        "user__email",
        "user__username",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("workspace", "user")


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "workspace",
        "channel_type",
        "created_at",
    )

    list_filter = (
        "channel_type",
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


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "channel",
        "author",
        "created_at",
    )

    search_fields = (
        "content",
        "author__email",
        "author__username",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "edited_at",
    )

    ordering = ("-created_at",)


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "message",
        "original_name",
        "size",
        "created_at",
    )

    search_fields = (
        "original_name",
        "message__author__email",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)