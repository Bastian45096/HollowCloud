from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.chat.models import Workspace
from apps.common.models import BaseModel


class Folder(BaseModel):
    """
    Carpeta dentro de un workspace.
    Soporta estructura jerárquica mediante parent.
    """

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="folders",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(
        max_length=255,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Folder"
        verbose_name_plural = "Folders"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "parent", "name"],
                name="unique_folder_name_per_parent",
            )
        ]

    def __str__(self) -> str:
        return self.name


class StoredFile(BaseModel):
    """
    Archivo almacenado en la plataforma.
    """

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="files",
    )
    folder = models.ForeignKey(
        Folder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="files",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_files",
    )
    name = models.CharField(
        max_length=255,
    )
    file = models.FileField(
        upload_to="storage/",
    )
    mime_type = models.CharField(
        max_length=100,
    )
    size = models.PositiveBigIntegerField()
    current_version = models.PositiveIntegerField(
        default=1,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Stored File"
        verbose_name_plural = "Stored Files"

    def __str__(self) -> str:
        return self.name


class FileVersion(BaseModel):
    """
    Historial de versiones de un archivo.
    """

    stored_file = models.ForeignKey(
        StoredFile,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    file = models.FileField(
        upload_to="storage_versions/",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="file_versions",
    )
    size = models.PositiveBigIntegerField()

    class Meta:
        ordering = ["-version_number"]
        verbose_name = "File Version"
        verbose_name_plural = "File Versions"
        constraints = [
            models.UniqueConstraint(
                fields=["stored_file", "version_number"],
                name="unique_file_version_number",
            )
        ]

    def __str__(self) -> str:
        return f"{self.stored_file.name} v{self.version_number}"


class FileShare(BaseModel):
    """
    Compartición de archivos con otros usuarios.
    """

    stored_file = models.ForeignKey(
        StoredFile,
        on_delete=models.CASCADE,
        related_name="shares",
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shared_files",
    )
    can_edit = models.BooleanField(
        default=False,
    )

    class Meta:
        verbose_name = "File Share"
        verbose_name_plural = "File Shares"
        constraints = [
            models.UniqueConstraint(
                fields=["stored_file", "shared_with"],
                name="unique_file_share",
            )
        ]

    def __str__(self) -> str:
        return f"{self.stored_file.name} shared with {self.shared_with.email}"