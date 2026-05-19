from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """
    Modelo abstracto que agrega timestamps automáticos.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    Modelo abstracto que usa UUID como clave primaria.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    """
    Modelo base del proyecto.
    Incluye:
    - id (UUID)
    - created_at
    - updated_at
    """

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Modelo abstracto para borrado lógico.
    """

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_deleted",
    )

    class Meta:
        abstract = True