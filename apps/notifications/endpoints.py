from django.shortcuts import render

# Create your views here.
# apps/notifications/endpoints.py

"""
Endpoints para la aplicación notifications.

Responsabilidades:
- Listar notificaciones del usuario autenticado
- Marcar notificaciones como leídas
- Eliminar notificaciones
- Gestionar preferencias de notificaciones
- Obtener resumen de notificaciones
"""

import logging
from uuid import UUID

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.common.exceptions import PermissionDeniedError

from .models import Notification, NotificationPreference
from .serializers import (
    NotificationSerializer,
    NotificationPreferenceSerializer,
    MarkNotificationReadSerializer,
)
from .services import (
    mark_notifications_as_read,
    delete_notification,
    update_notification_preferences,
)
from .selectors import (
    get_user_notifications,
    get_unread_notification_count,
    get_user_preferences,
    get_notification_summary,
    get_notification_by_id,
)

logger = logging.getLogger(__name__)


class NotificationListView(APIView):
    """
    Listar notificaciones del usuario autenticado.
    
    GET /api/notifications/
    
    Query params:
    - limit: int (default: 50)
    - offset: int (default: 0)
    - is_read: bool (True/False)
    - type: str (info, success, warning, error)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Obtiene notificaciones del usuario con paginación.
        """
        logger.info("=" * 60)
        logger.info("INICIO [NotificationListView] - Listando notificaciones")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info("=" * 60)

        try:
            # Obtener parámetros de consulta
            limit = int(request.query_params.get('limit', 50))
            offset = int(request.query_params.get('offset', 0))
            is_read_param = request.query_params.get('is_read')
            notification_type = request.query_params.get('type')

            # Convertir is_read a booleano
            is_read = None
            if is_read_param is not None:
                is_read = is_read_param.lower() == 'true'

            logger.info(f"PROCESO [NotificationListView] - Parámetros: limit={limit}, offset={offset}, is_read={is_read}, type={notification_type}")

            # Obtener notificaciones
            result = get_user_notifications(
                user_id=request.user.id,
                limit=limit,
                offset=offset,
                is_read=is_read,
                notification_type=notification_type,
            )

            # Serializar
            serializer = NotificationSerializer(
                result['notifications'],
                many=True,
                context={'request': request}
            )

            # Obtener contador de no leídos
            unread_count = get_unread_notification_count(request.user.id)

            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [NotificationListView] - {len(serializer.data)} notificaciones")
            logger.info("=" * 60)

            return Response({
                'notifications': serializer.data,
                'total': result['total'],
                'limit': result['limit'],
                'offset': result['offset'],
                'unread_count': unread_count,
            })

        except Exception as exc:
            logger.error("=" * 60)
            logger.error(f"ERROR [NotificationListView] - Error al listar notificaciones")
            logger.error(f"ERROR [NotificationListView] - Motivo: {str(exc)}")
            logger.error("=" * 60, exc_info=True)
            raise


class NotificationMarkReadView(APIView):
    """
    Marcar notificaciones como leídas.
    
    PATCH /api/notifications/mark-read/
    
    Body:
    {
        "notification_ids": ["uuid1", "uuid2"],  # opcional
        "mark_all": true/false                    # opcional
    }
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        """
        Marca notificaciones específicas o todas como leídas.
        """
        logger.info("=" * 60)
        logger.info("INICIO [NotificationMarkReadView] - Marcando notificaciones como leídas")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info(f"Datos recibidos: {request.data}")
        logger.info("=" * 60)

        try:
            # Validar datos
            serializer = MarkNotificationReadSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Marcar como leídas
            count = mark_notifications_as_read(
                user_id=request.user.id,
                notification_ids=serializer.validated_data.get('notification_ids'),
                mark_all=serializer.validated_data.get('mark_all', False),
            )

            # Obtener nuevo contador
            unread_count = get_unread_notification_count(request.user.id)

            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [NotificationMarkReadView] - {count} notificaciones marcadas como leídas")
            logger.info("=" * 60)

            return Response({
                'message': f'{count} notificaciones marcadas como leídas',
                'marked_count': count,
                'unread_count': unread_count,
            })

        except Exception as exc:
            logger.error("=" * 60)
            logger.error(f"ERROR [NotificationMarkReadView] - Error al marcar notificaciones")
            logger.error(f"ERROR [NotificationMarkReadView] - Motivo: {str(exc)}")
            logger.error("=" * 60, exc_info=True)
            raise


class NotificationDetailView(APIView):
    """
    Ver y eliminar una notificación específica.
    
    GET /api/notifications/{uuid}/
    DELETE /api/notifications/{uuid}/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, notification_id: UUID):
        """
        Obtiene una notificación específica.
        """
        logger.info("=" * 60)
        logger.info("INICIO [NotificationDetailView] - Obteniendo notificación")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info(f"Notificación ID: {notification_id}")
        logger.info("=" * 60)

        try:
            # Obtener notificación
            notification = get_notification_by_id(
                notification_id=notification_id,
                user_id=request.user.id,
            )

            if not notification:
                return Response(
                    {'error': 'Notificación no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Serializar
            serializer = NotificationSerializer(
                notification,
                context={'request': request}
            )

            logger.info("=" * 60)
            logger.info("FIN EXITOSO [NotificationDetailView] - Notificación obtenida")
            logger.info("=" * 60)

            return Response(serializer.data)

        except Exception as exc:
            logger.error("=" * 60)
            logger.error(f"ERROR [NotificationDetailView] - Error al obtener notificación")
            logger.error(f"ERROR [NotificationDetailView] - Motivo: {str(exc)}")
            logger.error("=" * 60, exc_info=True)
            raise

    def delete(self, request, notification_id: UUID):
        """
        Elimina una notificación específica.
        """
        logger.info("=" * 60)
        logger.info("INICIO [NotificationDetailView] - Eliminando notificación")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info(f"Notificación ID: {notification_id}")
        logger.info("=" * 60)

        try:
            # Eliminar notificación
            deleted = delete_notification(
                user_id=request.user.id,
                notification_id=notification_id,
            )

            if not deleted:
                return Response(
                    {'error': 'Notificación no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Obtener nuevo contador
            unread_count = get_unread_notification_count(request.user.id)

            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [NotificationDetailView] - Notificación eliminada")
            logger.info("=" * 60)

            return Response({
                'message': 'Notificación eliminada',
                'unread_count': unread_count,
            })

        except Exception as exc:
            logger.error("=" * 60)
            logger.error(f"ERROR [NotificationDetailView] - Error al eliminar notificación")
            logger.error(f"ERROR [NotificationDetailView] - Motivo: {str(exc)}")
            logger.error("=" * 60, exc_info=True)
            raise


class NotificationPreferenceView(APIView):
    """
    Gestionar preferencias de notificaciones.
    
    GET /api/notifications/preferences/
    PATCH /api/notifications/preferences/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Obtiene las preferencias de notificaciones del usuario.
        """
        logger.info("=" * 60)
        logger.info("INICIO [NotificationPreferenceView] - Obteniendo preferencias")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info("=" * 60)

        try:
            preferences = get_user_preferences(request.user.id)
            serializer = NotificationPreferenceSerializer(preferences)

            logger.info("=" * 60)
            logger.info("FIN EXITOSO [NotificationPreferenceView] - Preferencias obtenidas")
            logger.info("=" * 60)

            return Response(serializer.data)

        except Exception as exc:
            logger.error("=" * 60)
            logger.error(f"ERROR [NotificationPreferenceView] - Error al obtener preferencias")
            logger.error(f"ERROR [NotificationPreferenceView] - Motivo: {str(exc)}")
            logger.error("=" * 60, exc_info=True)
            raise

    def patch(self, request):
        """
        Actualiza las preferencias de notificaciones del usuario.
        """
        logger.info("=" * 60)
        logger.info("INICIO [NotificationPreferenceView] - Actualizando preferencias")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info(f"Datos recibidos: {request.data}")
        logger.info("=" * 60)

        try:
            # Validar datos
            serializer = NotificationPreferenceSerializer(
                data=request.data,
                partial=True,
            )
            serializer.is_valid(raise_exception=True)

            # Actualizar preferencias
            preferences = update_notification_preferences(
                user_id=request.user.id,
                email_enabled=serializer.validated_data.get('email_enabled'),
                in_app_enabled=serializer.validated_data.get('in_app_enabled'),
            )

            # Serializar resultado
            result_serializer = NotificationPreferenceSerializer(preferences)

            logger.info("=" * 60)
            logger.info("FIN EXITOSO [NotificationPreferenceView] - Preferencias actualizadas")
            logger.info("=" * 60)

            return Response(result_serializer.data)

        except Exception as exc:
            logger.error("=" * 60)
            logger.error(f"ERROR [NotificationPreferenceView] - Error al actualizar preferencias")
            logger.error(f"ERROR [NotificationPreferenceView] - Motivo: {str(exc)}")
            logger.error("=" * 60, exc_info=True)
            raise


class NotificationSummaryView(APIView):
    """
    Obtener resumen de notificaciones.
    
    GET /api/notifications/summary/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Obtiene un resumen de notificaciones para el usuario.
        """
        logger.info("=" * 60)
        logger.info("INICIO [NotificationSummaryView] - Obteniendo resumen")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info("=" * 60)

        try:
            summary = get_notification_summary(request.user.id)

            # Serializar notificaciones recientes
            recent_serializer = NotificationSerializer(
                summary['recent'],
                many=True,
                context={'request': request}
            )

            logger.info("=" * 60)
            logger.info("FIN EXITOSO [NotificationSummaryView] - Resumen obtenido")
            logger.info("=" * 60)

            return Response({
                'unread_count': summary['unread_count'],
                'has_unread': summary['has_unread'],
                'recent': recent_serializer.data,
                'unread_by_type': summary['unread_by_type'],
            })

        except Exception as exc:
            logger.error("=" * 60)
            logger.error(f"ERROR [NotificationSummaryView] - Error al obtener resumen")
            logger.error(f"ERROR [NotificationSummaryView] - Motivo: {str(exc)}")
            logger.error("=" * 60, exc_info=True)
            raise


class NotificationMarkSingleReadView(APIView):
    """
    Marcar una notificación específica como leída.
    
    PATCH /api/notifications/{uuid}/read/
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, notification_id: UUID):
        """
        Marca una notificación específica como leída.
        """
        logger.info("=" * 60)
        logger.info("INICIO [NotificationMarkSingleReadView] - Marcando notificación como leída")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info(f"Notificación ID: {notification_id}")
        logger.info("=" * 60)

        try:
            # Verificar que la notificación existe y pertenece al usuario
            notification = get_notification_by_id(
                notification_id=notification_id,
                user_id=request.user.id,
            )

            if not notification:
                return Response(
                    {'error': 'Notificación no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Marcar como leída
            count = mark_notifications_as_read(
                user_id=request.user.id,
                notification_ids=[notification_id],
            )

            # Obtener nuevo contador
            unread_count = get_unread_notification_count(request.user.id)

            logger.info("=" * 60)
            logger.info("FIN EXITOSO [NotificationMarkSingleReadView] - Notificación marcada como leída")
            logger.info("=" * 60)

            return Response({
                'message': 'Notificación marcada como leída',
                'unread_count': unread_count,
            })

        except Exception as exc:
            logger.error("=" * 60)
            logger.error(f"ERROR [NotificationMarkSingleReadView] - Error al marcar notificación")
            logger.error(f"ERROR [NotificationMarkSingleReadView] - Motivo: {str(exc)}")
            logger.error("=" * 60, exc_info=True)
            raise
