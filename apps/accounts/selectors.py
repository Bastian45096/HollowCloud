# apps/accounts/selectors.py

from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db import models

from .models import User

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTES DE CACHE PARA SELECTORS
# ============================================================

CACHE_USER_TTL = 3600  # 1 hora
CACHE_USER_PREFIX = "user_selector"


# ============================================================
# FUNCIONES DE CACHE
# ============================================================

def _get_user_cache_key(identifier: str, field: str) -> str:
    """Generar clave de cache para usuario"""
    return f"{CACHE_USER_PREFIX}:{field}:{identifier}"


def _get_cached_user(identifier: str, field: str) -> Optional[User]:
    """Obtener usuario de cache"""
    cache_key = _get_user_cache_key(identifier, field)
    user_id = cache.get(cache_key)
    
    if user_id:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            cache.delete(cache_key)
            return None
    return None


def _set_cached_user(user: User, identifier: str, field: str) -> None:
    """Guardar usuario en cache"""
    cache_key = _get_user_cache_key(identifier, field)
    cache.set(cache_key, user.id, CACHE_USER_TTL)


def _invalidate_user_cache(user: User) -> None:
    """Invalidar cache de usuario"""
    cache.delete(_get_user_cache_key(str(user.id), "id"))
    cache.delete(_get_user_cache_key(user.email, "email"))
    cache.delete(_get_user_cache_key(user.username, "username"))


# ============================================================
# SELECTORS CON CACHE
# ============================================================

@transaction.atomic
def get_user_by_id(*, user_id: int, use_cache: bool = True) -> User:
    """
    Obtener un usuario por su ID con cache.

    Args:
        user_id: ID del usuario
        use_cache: Si usar cache (True por defecto)

    Returns:
        User: Instancia del usuario

    Raises:
        ValidationError: Si el ID no es válido o el usuario no existe
    """
    logger.info("[GET Usuario] Buscando usuario user_id=%s", user_id)

    if not user_id:
        logger.warning("[GET Usuario] User ID es obligatorio")
        raise ValidationError("User ID es requerido")

    try:
        # Intentar obtener de cache
        if use_cache:
            user = _get_cached_user(str(user_id), "id")
            if user:
                logger.info("[GET Usuario] Usuario encontrado en cache user_id=%s", user_id)
                return user

        # Buscar en BD
        user = User.objects.filter(id=user_id).first()

        if user is None:
            logger.warning("[GET Usuario] Usuario no encontrado user_id=%s", user_id)
            raise ValidationError("Usuario no encontrado")

        # Guardar en cache
        if use_cache:
            _set_cached_user(user, str(user_id), "id")

        logger.info("[GET Usuario] Usuario encontrado exitosamente user_id=%s", user_id)
        return user

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[GET Usuario] Error inesperado: %s", str(exc), exc_info=True)
        raise


@transaction.atomic
def get_user_by_email(*, email: str, use_cache: bool = True) -> User:
    """
    Obtener un usuario por su email con cache.

    Args:
        email: Email del usuario
        use_cache: Si usar cache (True por defecto)

    Returns:
        User: Instancia del usuario

    Raises:
        ValidationError: Si el email no es válido o el usuario no existe
    """
    logger.info("[GET Usuario] Buscando usuario por email=%s", email)

    # Normalizar email
    email = email.strip().lower() if email else ''

    if not email:
        logger.warning("[GET Usuario] Email es obligatorio")
        raise ValidationError("Email es requerido")

    try:
        # Intentar obtener de cache
        if use_cache:
            user = _get_cached_user(email, "email")
            if user:
                logger.info("[GET Usuario] Usuario encontrado en cache email=%s", email)
                return user

        # Buscar en BD
        user = User.objects.filter(email=email).first()

        if user is None:
            logger.warning("[GET Usuario] Usuario no encontrado email=%s", email)
            raise ValidationError("Usuario no encontrado")

        # Guardar en cache
        if use_cache:
            _set_cached_user(user, email, "email")

        logger.info("[GET Usuario] Usuario encontrado exitosamente user_id=%s", user.id)
        return user

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[GET Usuario] Error inesperado: %s", str(exc), exc_info=True)
        raise


@transaction.atomic
def get_user_by_username(*, username: str, use_cache: bool = True) -> User:
    """
    Obtener un usuario por su username con cache.

    Args:
        username: Nombre de usuario
        use_cache: Si usar cache (True por defecto)

    Returns:
        User: Instancia del usuario

    Raises:
        ValidationError: Si el username no es válido o el usuario no existe
    """
    logger.info("[GET Usuario] Buscando usuario por username=%s", username)

    # Normalizar username
    username = username.strip().lower() if username else ''

    if not username:
        logger.warning("[GET Usuario] Username es obligatorio")
        raise ValidationError("Username es requerido")

    try:
        # Intentar obtener de cache
        if use_cache:
            user = _get_cached_user(username, "username")
            if user:
                logger.info("[GET Usuario] Usuario encontrado en cache username=%s", username)
                return user

        # Buscar en BD
        user = User.objects.filter(username=username).first()

        if user is None:
            logger.warning("[GET Usuario] Usuario no encontrado username=%s", username)
            raise ValidationError("Usuario no encontrado")

        # Guardar en cache
        if use_cache:
            _set_cached_user(user, username, "username")

        logger.info("[GET Usuario] Usuario encontrado exitosamente user_id=%s", user.id)
        return user

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[GET Usuario] Error inesperado: %s", str(exc), exc_info=True)
        raise


# ============================================================
# SELECTOR ADICIONAL: LISTAR USUARIOS
# ============================================================

def get_users(
    *,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Listar usuarios con filtros opcionales.

    Args:
        search: Búsqueda por email o username (parcial)
        is_active: Filtrar por estado activo
        is_verified: Filtrar por verificación
        limit: Límite de resultados
        offset: Offset para paginación

    Returns:
        Dict con usuarios y metadata
    """
    logger.info("[GET Usuarios] Listando usuarios con filtros")

    try:
        queryset = User.objects.all()

        # Aplicar filtros
        if search:
            queryset = queryset.filter(
                models.Q(email__icontains=search) |
                models.Q(username__icontains=search)
            )

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified)

        # Contar total
        total = queryset.count()

        # Paginar
        users = queryset[offset:offset + limit]

        logger.info("[GET Usuarios] Encontrados %d usuarios", total)

        return {
            "users": users,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as exc:
        logger.error("[GET Usuarios] Error inesperado: %s", str(exc), exc_info=True)
        raise


# ============================================================
# FUNCIÓN AUXILIAR PARA DEBUG
# ============================================================

def get_user_cache_status(identifier: str, field: str = "email") -> Dict[str, Any]:
    """
    Verificar estado de cache para un usuario (debug).
    """
    cache_key = _get_user_cache_key(identifier, field)
    user_id = cache.get(cache_key)
    
    return {
        "identifier": identifier,
        "field": field,
        "cache_key": cache_key,
        "cached": user_id is not None,
        "user_id": user_id,
    }