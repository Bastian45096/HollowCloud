from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class AuditLog(BaseModel):
    """
    Registro de auditoría de acciones realizadas en el sistema.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(
        max_length=100,
        db_index=True,
    )
    entity_type = models.CharField(
        max_length=100,
        db_index=True,
    )
    entity_id = models.CharField(
        max_length=100,
        db_index=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["entity_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        user_repr = self.user.email if self.user else "Anonymous"
        return f"{self.action} - {self.entity_type} ({user_repr})"