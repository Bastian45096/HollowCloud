# apps/notifications/selectors.py

"""
Selectors para la aplicación notifications.

Responsabilidades:
- Obtener notificaciones de usuarios con filtros
- Contar notificaciones no leídas
- Obtener preferencias de notificaciones
- Cachear resultados para optimizar rendimiento
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from django.db.models import Q
from django.core.cache import cache
from django.contrib.auth import get_user_model

from .models import Notification, NotificationPreference

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTES DE CACHE
# ============================================================

CACHE_UNREAD_TTL = 60  # 60 segundos
CACHE_UNREAD_PREFIX = "unread_notifications"
CACHE_PREFERENCES_TTL = 3600  # 1 hora
CACHE_PREFERENCES_PREFIX = "notification_preferences"


# ============================================================
# FUNCIONES AUXILIARES DE CACHE
# ============================================================

def _get_unread_cache_key(user_id: UUID) -> str:
    """Genera la clave de cache para el contador de no leídos."""
    return f"{CACHE_UNREAD_PREFIX}:{user_id}"


def _get_preferences_cache_key(user_id: UUID) -> str:
    """Genera la clave de cache para las preferencias."""
    return f"{CACHE_PREFERENCES_PREFIX}:{user_id}"


# ============================================================
# SELECTORS PRINCIPALES
# ============================================================

def get_user_notifications(
    *,
    user_id: UUID,
    limit: int = 50,
    offset: int = 0,
    is_read: Optional[bool] = None,
    notification_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Obtiene notificaciones de un usuario con filtros opcionales.
    
    Args:
        user_id: UUID del usuario
        limit: Límite de resultados (por defecto 50)
        offset: Offset para paginación (por defecto 0)
        is_read: Filtrar por estado de lectura (True/False/None)
        notification_type: Filtrar por tipo de notificación
    
    Returns:
        Dict con notificaciones, total, limit y offset
    """
    logger.info("=" * 60)
    logger.info("INICIO [GetUserNotifications] - Obteniendo notificaciones")
    logger.info(f"Usuario ID: {user_id}")
    logger.info(f"Límite: {limit}, Offset: {offset}")
    logger.info(f"Filtros - Leído: {is_read}, Tipo: {notification_type}")
    logger.info("=" * 60)

    try:
        # Verificar que el usuario existe
        if not User.objects.filter(id=user_id).exists():
            logger.warning(f"WARNING [GetUserNotifications] - Usuario no encontrado: {user_id}")
            return {
                "notifications": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
            }

        # Construir queryset base
        queryset = Notification.objects.filter(user_id=user_id)

        # Aplicar filtros
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read)
            logger.info(f"PROCESO [GetUserNotifications] - Filtro por lectura: {is_read}")

        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
            logger.info(f"PROCESO [GetUserNotifications] - Filtro por tipo: {notification_type}")

        # Obtener total
        total = queryset.count()
        logger.info(f"PROCESO [GetUserNotifications] - Total notificaciones: {total}")

        # Aplicar orden y paginación
        notifications = list(
            queryset
            .select_related('user')
            .order_by('-created_at')[offset:offset + limit]
        )

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [GetUserNotifications] - Obtenidas {len(notifications)} notificaciones")
        logger.info("=" * 60)

        return {
            "notifications": notifications,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [GetUserNotifications] - Error al obtener notificaciones")
        logger.error(f"ERROR [GetUserNotifications] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        raise


def get_unread_notification_count(user_id: UUID) -> int:
    """
    Obtiene el número de notificaciones no leídas de un usuario.
    
    Utiliza cache para optimizar consultas frecuentes.
    
    Args:
        user_id: UUID del usuario
    
    Returns:
        int: Número de notificaciones no leídas
    """
    logger.debug(f"DEBUG [GetUnreadCount] - Obteniendo contador para usuario {user_id}")

    try:
        # Intentar obtener de cache
        cache_key = _get_unread_cache_key(user_id)
        count = cache.get(cache_key)

        if count is not None:
            logger.debug(f"DEBUG [GetUnreadCount] - Cache hit para usuario {user_id}: {count}")
            return count

        # Cache miss: consultar base de datos
        count = Notification.objects.filter(
            user_id=user_id,
            is_read=False
        ).count()

        # Guardar en cache
        cache.set(cache_key, count, CACHE_UNREAD_TTL)
        logger.debug(f"DEBUG [GetUnreadCount] - Cache miss, contador: {count}")

        return count

    except Exception as exc:
        logger.error(f"ERROR [GetUnreadCount] - Error para usuario {user_id}: {str(exc)}")
        # En caso de error, consultar directamente (sin cache)
        try:
            return Notification.objects.filter(
                user_id=user_id,
                is_read=False
            ).count()
        except:
            return 0


def get_user_preferences(user_id: UUID) -> NotificationPreference:
    """
    Obtiene o crea las preferencias de notificaciones de un usuario.
    
    Utiliza cache para optimizar consultas frecuentes.
    
    Args:
        user_id: UUID del usuario
    
    Returns:
        NotificationPreference: Preferencias del usuario
    """
    logger.debug(f"DEBUG [GetUserPreferences] - Obteniendo preferencias para usuario {user_id}")

    try:
        # Intentar obtener de cache
        cache_key = _get_preferences_cache_key(user_id)
        preferences = cache.get(cache_key)

        if preferences is not None:
            logger.debug(f"DEBUG [GetUserPreferences] - Cache hit para usuario {user_id}")
            return preferences

        # Cache miss: consultar base de datos
        preferences, created = NotificationPreference.objects.get_or_create(
            user_id=user_id,
            defaults={
                'email_enabled': True,
                'in_app_enabled': True,
            }
        )

        if created:
            logger.info(f"INFO [GetUserPreferences] - Preferencias creadas para usuario {user_id}")

        # Guardar en cache
        cache.set(cache_key, preferences, CACHE_PREFERENCES_TTL)
        logger.debug(f"DEBUG [GetUserPreferences] - Cache miss, preferencias obtenidas de BD")

        return preferences

    except Exception as exc:
        logger.error(f"ERROR [GetUserPreferences] - Error para usuario {user_id}: {str(exc)}")
        # Fallback: crear/obtener directamente
        preferences, _ = NotificationPreference.objects.get_or_create(
            user_id=user_id,
            defaults={
                'email_enabled': True,
                'in_app_enabled': True,
            }
        )
        return preferences


def get_notification_by_id(
    *,
    notification_id: UUID,
    user_id: Optional[UUID] = None,
) -> Optional[Notification]:
    """
    Obtiene una notificación por su ID.
    
    Args:
        notification_id: UUID de la notificación
        user_id: UUID del usuario (opcional, para verificar pertenencia)
    
    Returns:
        Notification o None si no existe
    """
    logger.debug(f"DEBUG [GetNotificationById] - Buscando notificación {notification_id}")

    try:
        queryset = Notification.objects.select_related('user')

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        notification = queryset.get(id=notification_id)
        logger.debug(f"DEBUG [GetNotificationById] - Notificación encontrada: {notification_id}")
        return notification

    except Notification.DoesNotExist:
        logger.warning(f"WARNING [GetNotificationById] - Notificación no encontrada: {notification_id}")
        return None
    except Exception as exc:
        logger.error(f"ERROR [GetNotificationById] - Error: {str(exc)}")
        return None


def get_notifications_by_type(
    *,
    user_id: UUID,
    notification_type: str,
    limit: int = 50,
) -> List[Notification]:
    """
    Obtiene notificaciones de un tipo específico para un usuario.
    
    Args:
        user_id: UUID del usuario
        notification_type: Tipo de notificación a filtrar
        limit: Límite de resultados
    
    Returns:
        List[Notification]: Lista de notificaciones
    """
    logger.debug(f"DEBUG [GetNotificationsByType] - Buscando tipo {notification_type} para usuario {user_id}")

    try:
        notifications = list(
            Notification.objects.filter(
                user_id=user_id,
                notification_type=notification_type
            )
            .select_related('user')
            .order_by('-created_at')[:limit]
        )

        logger.debug(f"DEBUG [GetNotificationsByType] - Encontradas {len(notifications)} notificaciones")
        return notifications

    except Exception as exc:
        logger.error(f"ERROR [GetNotificationsByType] - Error: {str(exc)}")
        return []


def get_recent_notifications(
    *,
    user_id: UUID,
    limit: int = 10,
    hours: int = 24,
) -> List[Notification]:
    """
    Obtiene notificaciones recientes de un usuario.
    
    Args:
        user_id: UUID del usuario
        limit: Límite de resultados
        hours: Horas hacia atrás a considerar
    
    Returns:
        List[Notification]: Lista de notificaciones recientes
    """
    from django.utils import timezone
    from datetime import timedelta

    logger.debug(f"DEBUG [GetRecentNotifications] - Buscando notificaciones recientes para usuario {user_id}")

    try:
        cutoff_time = timezone.now() - timedelta(hours=hours)

        notifications = list(
            Notification.objects.filter(
                user_id=user_id,
                created_at__gte=cutoff_time
            )
            .select_related('user')
            .order_by('-created_at')[:limit]
        )

        logger.debug(f"DEBUG [GetRecentNotifications] - Encontradas {len(notifications)} notificaciones recientes")
        return notifications

    except Exception as exc:
        logger.error(f"ERROR [GetRecentNotifications] - Error: {str(exc)}")
        return []


def has_unread_notifications(user_id: UUID) -> bool:
    """
    Verifica si un usuario tiene notificaciones no leídas.
    
    Args:
        user_id: UUID del usuario
    
    Returns:
        bool: True si tiene notificaciones no leídas
    """
    count = get_unread_notification_count(user_id)
    return count > 0


def get_notification_summary(user_id: UUID) -> Dict[str, Any]:
    """
    Obtiene un resumen de notificaciones para un usuario.
    
    Args:
        user_id: UUID del usuario
    
    Returns:
        Dict con resumen de notificaciones
    """
    logger.debug(f"DEBUG [GetNotificationSummary] - Generando resumen para usuario {user_id}")

    try:
        unread_count = get_unread_notification_count(user_id)
        recent = get_recent_notifications(user_id=user_id, limit=5)

        # Contar por tipo
        type_counts = {}
        for notification_type, _ in Notification.Type.choices:
            count = Notification.objects.filter(
                user_id=user_id,
                notification_type=notification_type,
                is_read=False
            ).count()
            if count > 0:
                type_counts[notification_type] = count

        return {
            "unread_count": unread_count,
            "has_unread": unread_count > 0,
            "recent": recent,
            "unread_by_type": type_counts,
        }

    except Exception as exc:
        logger.error(f"ERROR [GetNotificationSummary] - Error: {str(exc)}")
        return {
            "unread_count": 0,
            "has_unread": False,
            "recent": [],
            "unread_by_type": {},
        }