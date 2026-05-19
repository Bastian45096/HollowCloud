from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import BaseModel


class User(AbstractUser, BaseModel):
    """
    Modelo de usuario personalizado de HollCloud.
    Usa email como campo principal de autenticación.
    """

    email = models.EmailField(
        unique=True,
        db_index=True,
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
    )
    bio = models.TextField(
        blank=True,
    )
    is_verified = models.BooleanField(
        default=False,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return self.email


class Profile(BaseModel):
    """
    Información adicional del usuario.
    """

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="profile",
    )
    timezone = models.CharField(
        max_length=64,
        default="America/Santiago",
    )
    language = models.CharField(
        max_length=10,
        default="es",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"

    def __str__(self) -> str:
        return f"Profile<{self.user.email}>"