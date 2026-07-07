from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone 
from apps.common.models import BaseModel
from datetime import timedelta

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
    
    Estados:
    - PENDING:  Invitación enviada, esperando aceptación
    - ACTIVE:   Usuario miembro activo del workspace
    - REJECTED: Invitación rechazada
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        ACTIVE = "active", "Activo"
        REJECTED = "rejected", "Rechazado"

    # ============================================================
    # CAMPOS
    # ============================================================
    
    workspace = models.ForeignKey(
        "Workspace",
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
    
    # 🔥 NUEVOS CAMPOS PARA INVITACIONES
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invited_members",
    )
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de expiración de la invitación (7 días por defecto)",
    )

    # ============================================================
    # META
    # ============================================================

    class Meta:
        ordering = ["workspace", "user"]
        verbose_name = "Workspace Member"
        verbose_name_plural = "Workspace Members"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user"],
                name="unique_workspace_member",
            ),
            # ✅ ELIMINADO: MySQL no soporta condition
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["expires_at"]),
        ]

    # ============================================================
    # MÉTODOS
    # ============================================================

    def __str__(self) -> str:
        return f"{self.user.email} in {self.workspace.name} ({self.role}) - {self.status}"

    def is_expired(self) -> bool:
        """Verificar si la invitación ha expirado"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    def is_pending(self) -> bool:
        """Verificar si la invitación está pendiente"""
        return self.status == self.Status.PENDING

    def is_active(self) -> bool:
        """Verificar si el usuario es miembro activo"""
        return self.status == self.Status.ACTIVE

    def is_rejected(self) -> bool:
        """Verificar si la invitación fue rechazada"""
        return self.status == self.Status.REJECTED

    def accept(self) -> None:
        """
        Aceptar invitación → Cambiar a ACTIVE
        """
        if not self.is_pending():
            raise ValueError("La invitación no está pendiente")
        
        if self.is_expired():
            raise ValueError("La invitación ha expirado")
        
        self.status = self.Status.ACTIVE
        self.save(update_fields=["status", "updated_at"])

    def reject(self) -> None:
        """
        Rechazar invitación → Cambiar a REJECTED
        """
        if not self.is_pending():
            raise ValueError("La invitación no está pendiente")
        
        self.status = self.Status.REJECTED
        self.save(update_fields=["status", "updated_at"])

    def expire(self) -> None:
        """
        Marcar como expirada (cuando la fecha de expiración ha pasado)
        """
        if self.is_expired() and self.is_pending():
            self.status = self.Status.REJECTED
            self.save(update_fields=["status", "updated_at"])

    @classmethod
    def create_invitation(
        cls,
        workspace,
        user,
        invited_by,
        role: str = Role.MEMBER,
        days_valid: int = 7,
    ) -> "WorkspaceMember":
        """
        Crear una nueva invitación (estado PENDING)
        """
        return cls.objects.create(
            workspace=workspace,
            user=user,
            role=role,
            status=cls.Status.PENDING,
            invited_by=invited_by,
            expires_at=timezone.now() + timezone.timedelta(days=days_valid),
        )

    @classmethod
    def get_pending_invitations(cls, user):
        """Obtener todas las invitaciones pendientes de un usuario"""
        return cls.objects.filter(
            user=user,
            status=cls.Status.PENDING,
            expires_at__gt=timezone.now(),
        ).select_related("workspace", "invited_by")

    @classmethod
    def get_active_members(cls, workspace):
        """Obtener todos los miembros activos de un workspace"""
        return cls.objects.filter(
            workspace=workspace,
            status=cls.Status.ACTIVE,
        ).select_related("user")

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