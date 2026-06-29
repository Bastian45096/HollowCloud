# apps/common/validators.py

import re
from django.core.exceptions import ValidationError


def validate_username(value):
    """Validar que el username solo contenga caracteres permitidos"""
    if not re.match(r'^[a-zA-Z0-9_.-]+$', value):
        raise ValidationError(
            "El nombre de usuario solo puede contener letras, números, guiones y guiones bajos"
        )


def validate_file_size(value, max_size_mb=5):
    """Validar que el archivo no exceda el tamaño máximo"""
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            f"El archivo no puede superar los {max_size_mb}MB"
        )


def validate_positive_number(value):
    """Validar que el número sea positivo"""
    if value <= 0:
        raise ValidationError("El valor debe ser mayor a cero")


def validate_not_empty(value):
    """Validar que el campo no esté vacío"""
    if not value or not value.strip():
        raise ValidationError("Este campo no puede estar vacío")