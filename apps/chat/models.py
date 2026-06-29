from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Workspace(BaseModel):
    """
    Espacio de trabajo principal donde los usuarios colaboran.
    """

    name = models.CharField(
        max_length=255,
    )
    slug = models.SlugField(
        unique=True,
        db_index=True,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_workspaces",
    )
    description = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Workspace"
        verbose_name_plural = "Workspaces"

    def __str__(self) -> str:
        return self.name


class WorkspaceMember(BaseModel):
    """
    Relación entre un usuario y un workspace.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )

    class Meta:
        ordering = ["workspace", "user"]
        verbose_name = "Workspace Member"
        verbose_name_plural = "Workspace Members"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user"],
                name="unique_workspace_member",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user.email} in {self.workspace.name} ({self.role})"


class Channel(BaseModel):
    """
    Canal dentro de un workspace.
    """

    class Type(models.TextChoices):
        TEXT = "text", "Text"
        VOICE = "voice", "Voice"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="channels",
    )
    name = models.CharField(
        max_length=255,
    )
    slug = models.SlugField()
    channel_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.TEXT,
    )
    description = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Channel"
        verbose_name_plural = "Channels"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "slug"],
                name="unique_channel_slug_per_workspace",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Message(BaseModel):
    """
    Mensaje enviado en un canal.
    """

    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    content = models.TextField(blank=True, null=True)
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self) -> str:
        return f"Message by {self.author.email}"


class MessageAttachment(BaseModel):
    """
    Archivos adjuntos a un mensaje.
    """

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(
        upload_to="chat_attachments/",
    )
    original_name = models.CharField(
        max_length=255,
    )
    mime_type = models.CharField(
        max_length=100,
    )
    size = models.PositiveBigIntegerField()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Message Attachment"
        verbose_name_plural = "Message Attachments"

    def __str__(self) -> str:
        return self.original_name