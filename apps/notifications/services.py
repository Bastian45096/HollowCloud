# apps/notifications/services.py

"""
Servicios para la aplicación notifications.

Responsabilidades:
- Crear notificaciones
- Marcar notificaciones como leídas
- Gestionar preferencias de notificaciones
- Notificaciones específicas del sistema
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.chat.models import WorkspaceMember
import json

from .models import Notification, NotificationPreference
from apps.chat.models import Workspace
from .selectors import get_user_preferences

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def _invalidate_unread_cache(user_id: UUID) -> None:
    """
    Invalida la caché de notificaciones no leídas para un usuario.
    
    Esto fuerza que la próxima consulta del contador no leído
    se obtenga directamente de la base de datos.
    """
    cache_key = f"unread_notifications:{user_id}"
    cache.delete(cache_key)
    logger.debug(f"Cache invalidada para usuario {user_id}")


# ============================================================
# SERVICIOS PRINCIPALES
# ============================================================

@transaction.atomic
def create_notification(
    *,
    user_id: UUID,
    title: str,
    message: str,
    notification_type: str = Notification.Type.INFO,
) -> Optional[Notification]:
    """
    Crea una notificación para un usuario.
    
    Responsabilidades:
    - Verificar que el usuario exista
    - Verificar que el tipo de notificación sea válido
    - Crear la notificación en la base de datos
    - Invalidar la caché de contador no leído
    
    Args:
        user_id: UUID del usuario destinatario
        title: Título de la notificación
        message: Mensaje de la notificación
        notification_type: Tipo de notificación (INFO, SUCCESS, WARNING, ERROR)
    
    Returns:
        Notification: La notificación creada, o None si el usuario no existe
    """
    logger.info("=" * 60)
    logger.info("INICIO [CreateNotification] - Creando notificación")
    logger.info(f"Usuario ID: {user_id}")
    logger.info(f"Título: {title}")
    logger.info(f"Tipo: {notification_type}")
    logger.info("=" * 60)

    # Validar que el tipo sea válido
    valid_types = [choice[0] for choice in Notification.Type.choices]
    if notification_type not in valid_types:
        logger.error(f"ERROR [CreateNotification] - Tipo inválido: {notification_type}")
        raise ValueError(f"Tipo de notificación inválido: {notification_type}")

    try:
        # Verificar que el usuario existe
        user = User.objects.get(id=user_id)
        logger.info(f"PROCESO [CreateNotification] - Usuario encontrado: {user.email}")

        # Verificar preferencias del usuario
        preferences = get_user_preferences(user_id=user_id)
        
        # Si el usuario tiene desactivadas las notificaciones en la app, no crear
        if not preferences.in_app_enabled:
            logger.info(f"INFO [CreateNotification] - Notificaciones in-app desactivadas para {user.email}")
            return None

        # Crear la notificación
        notification = Notification.objects.create(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
        )

        # Invalidar caché de contador no leído
        _invalidate_unread_cache(user_id=user_id)

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [CreateNotification] - Notificación creada: {notification.id}")
        logger.info("=" * 60)

        # TODO: Enviar notificación en tiempo real con WebSocket
        # from apps.notifications.consumers import send_notification
        # await send_notification(user_id, notification)

        return notification

    except User.DoesNotExist:
        logger.error(f"ERROR [CreateNotification] - Usuario no encontrado: {user_id}")
        return None
    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [CreateNotification] - Error al crear notificación")
        logger.error(f"ERROR [CreateNotification] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        raise


@transaction.atomic
def mark_notifications_as_read(
    *,
    user_id: UUID,
    notification_ids: Optional[List[UUID]] = None,
    mark_all: bool = False,
) -> int:
    """
    Marca notificaciones como leídas.
    
    Responsabilidades:
    - Marcar notificaciones específicas o todas
    - Actualizar read_at con la fecha/hora actual
    - Invalidar caché de contador no leído
    
    Args:
        user_id: UUID del usuario
        notification_ids: Lista de IDs de notificaciones a marcar
        mark_all: Si es True, marca TODAS las notificaciones como leídas
    
    Returns:
        int: Número de notificaciones marcadas como leídas
    """
    logger.info("=" * 60)
    logger.info("INICIO [MarkNotificationsAsRead] - Marcando como leídas")
    logger.info(f"Usuario ID: {user_id}")
    logger.info(f"Marcar todas: {mark_all}")
    logger.info(f"IDs específicas: {notification_ids if notification_ids else 'Ninguna'}")
    logger.info("=" * 60)

    # Construir queryset base (solo notificaciones no leídas del usuario)
    queryset = Notification.objects.filter(
        user_id=user_id,
        is_read=False
    )

    if mark_all:
        logger.info("PROCESO [MarkNotificationsAsRead] - Marcando TODAS como leídas")
    elif notification_ids:
        queryset = queryset.filter(id__in=notification_ids)
        logger.info(f"PROCESO [MarkNotificationsAsRead] - Marcando {len(notification_ids)} notificaciones específicas")
    else:
        logger.info("PROCESO [MarkNotificationsAsRead] - Sin IDs específicos, no se marcará nada")
        return 0

    # Actualizar las notificaciones
    now = timezone.now()
    count = queryset.update(is_read=True, read_at=now)

    # Invalidar caché de contador no leído
    _invalidate_unread_cache(user_id=user_id)

    logger.info("=" * 60)
    logger.info(f"FIN EXITOSO [MarkNotificationsAsRead] - {count} notificaciones marcadas como leídas")
    logger.info("=" * 60)

    return count


@transaction.atomic
def delete_notification(
    *,
    user_id: UUID,
    notification_id: UUID,
) -> bool:
    """
    Elimina una notificación específica de un usuario.
    
    Args:
        user_id: UUID del usuario
        notification_id: UUID de la notificación a eliminar
    
    Returns:
        bool: True si la notificación fue eliminada, False si no existe
    """
    logger.info("=" * 60)
    logger.info("INICIO [DeleteNotification] - Eliminando notificación")
    logger.info(f"Usuario ID: {user_id}")
    logger.info(f"Notificación ID: {notification_id}")
    logger.info("=" * 60)

    try:
        # Verificar que la notificación pertenece al usuario
        notification = Notification.objects.get(
            id=notification_id,
            user_id=user_id
        )
        
        was_read = notification.is_read
        notification.delete()
        
        # Si la notificación no estaba leída, invalidar caché
        if not was_read:
            _invalidate_unread_cache(user_id=user_id)

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [DeleteNotification] - Notificación eliminada: {notification_id}")
        logger.info("=" * 60)
        return True

    except Notification.DoesNotExist:
        logger.warning(f"WARNING [DeleteNotification] - Notificación no encontrada: {notification_id}")
        return False
    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [DeleteNotification] - Error al eliminar notificación")
        logger.error(f"ERROR [DeleteNotification] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        raise


@transaction.atomic
def update_notification_preferences(
    *,
    user_id: UUID,
    email_enabled: Optional[bool] = None,
    in_app_enabled: Optional[bool] = None,
) -> NotificationPreference:
    """
    Actualiza las preferencias de notificaciones de un usuario.
    
    Args:
        user_id: UUID del usuario
        email_enabled: Activar/desactivar notificaciones por email
        in_app_enabled: Activar/desactivar notificaciones en la app
    
    Returns:
        NotificationPreference: Las preferencias actualizadas
    """
    logger.info("=" * 60)
    logger.info("INICIO [UpdateNotificationPreferences] - Actualizando preferencias")
    logger.info(f"Usuario ID: {user_id}")
    logger.info(f"Email enabled: {email_enabled}")
    logger.info(f"In-app enabled: {in_app_enabled}")
    logger.info("=" * 60)

    try:
        # Obtener o crear preferencias
        preferences = get_user_preferences(user_id=user_id)

        # Actualizar campos
        if email_enabled is not None:
            preferences.email_enabled = email_enabled
            logger.info(f"PROCESO [UpdateNotificationPreferences] - Email enabled: {email_enabled}")

        if in_app_enabled is not None:
            preferences.in_app_enabled = in_app_enabled
            logger.info(f"PROCESO [UpdateNotificationPreferences] - In-app enabled: {in_app_enabled}")

        preferences.save()

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [UpdateNotificationPreferences] - Preferencias actualizadas")
        logger.info("=" * 60)

        return preferences

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [UpdateNotificationPreferences] - Error al actualizar preferencias")
        logger.error(f"ERROR [UpdateNotificationPreferences] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        raise


# ============================================================
# NOTIFICACIONES ESPECÍFICAS
# ============================================================

def notify_user_registered(user: User) -> Optional[Notification]:
    """
    Envía notificación de bienvenida al usuario recién registrado.
    """
    logger.info(f"INFO [NotifyUserRegistered] - Enviando bienvenida a {user.email}")

    return create_notification(
        user_id=user.id,
        title="¡Bienvenido a HollCloud!",
        message="Tu cuenta ha sido creada exitosamente. Explora los workspaces y comienza a colaborar.",
        notification_type=Notification.Type.SUCCESS,
    )


def notify_user_joined_workspace(
    user: User,
    workspace_name: str,
    workspace_id: UUID,
) -> Optional[Notification]:
    """
    Notifica a un usuario que se ha unido a un workspace.
    """
    logger.info(f"INFO [NotifyUserJoinedWorkspace] - {user.email} se unió a {workspace_name}")

    return create_notification(
        user_id=user.id,
        title=f"Te has unido a \"{workspace_name}\"",
        message=f"Ahora eres miembro del workspace \"{workspace_name}\". ¡Empieza a colaborar!",
        notification_type=Notification.Type.SUCCESS,
    )


def notify_user_left_workspace(
    user: User,
    workspace_name: str,
) -> Optional[Notification]:
    """
    Notifica a un usuario que ha abandonado un workspace.
    """
    logger.info(f"INFO [NotifyUserLeftWorkspace] - {user.email} abandonó {workspace_name}")

    return create_notification(
        user_id=user.id,
        title=f"Has abandonado \"{workspace_name}\"",
        message=f"Has abandonado el workspace \"{workspace_name}\". Puedes volver a unirte cuando quieras.",
        notification_type=Notification.Type.INFO,
    )


def notify_user_expelled_from_workspace(
    user: User,
    workspace_name: str,
    workspace_id: UUID,
    expelled_by: str,
) -> Optional[Notification]:
    """
    Notifica a un usuario que ha sido expulsado de un workspace.
    """
    logger.info(f"INFO [NotifyUserExpelled] - {user.email} expulsado de {workspace_name} por {expelled_by}")

    return create_notification(
        user_id=user.id,
        title=f"Has sido expulsado de \"{workspace_name}\"",
        message=f"{expelled_by} te ha expulsado del workspace \"{workspace_name}\".",
        notification_type=Notification.Type.ERROR,
    )


def notify_user_role_changed(
    user: User,
    workspace_name: str,
    workspace_id: UUID,
    new_role: str,
    changed_by: str,
) -> Optional[Notification]:
    """
    Notifica a un usuario que su rol ha cambiado en un workspace.
    """
    role_display = {
        'owner': 'Propietario',
        'admin': 'Administrador',
        'member': 'Miembro'
    }.get(new_role, new_role)

    logger.info(f"INFO [NotifyUserRoleChanged] - {user.email} ahora es {new_role} en {workspace_name}")

    return create_notification(
        user_id=user.id,
        title=f"Tu rol ha cambiado en \"{workspace_name}\"",
        message=f"{changed_by} te ha asignado el rol de {role_display} en el workspace \"{workspace_name}\".",
        notification_type=Notification.Type.INFO,
    )


def notify_user_workspace_deleted(
    user: User,
    workspace_name: str,
    workspace_id: UUID,
    deleted_by: str,
) -> Optional[Notification]:
    """
    Notifica a los miembros que un workspace ha sido eliminado.
    """
    logger.info(f"INFO [NotifyUserWorkspaceDeleted] - {workspace_name} eliminado por {deleted_by}")

    return create_notification(
        user_id=user.id,
        title=f"Workspace \"{workspace_name}\" eliminado",
        message=f"{deleted_by} ha eliminado el workspace \"{workspace_name}\".",
        notification_type=Notification.Type.WARNING,
    )


def notify_user_channel_created(
    user: User,
    workspace_name: str,
    channel_name: str,
    workspace_id: UUID,
    created_by: str,
) -> Optional[Notification]:
    """
    Notifica a los miembros que se ha creado un nuevo canal.
    """
    logger.info(f"INFO [NotifyUserChannelCreated] - {channel_name} creado en {workspace_name} por {created_by}")

    return create_notification(
        user_id=user.id,
        title=f"Nuevo canal: {channel_name}",
        message=f"{created_by} ha creado el canal \"{channel_name}\" en el workspace \"{workspace_name}\".",
        notification_type=Notification.Type.INFO,
    )


def notify_user_channel_deleted(
    user: User,
    workspace_name: str,
    channel_name: str,
    workspace_id: UUID,
    deleted_by: str,
) -> Optional[Notification]:
    """
    Notifica a los miembros que un canal ha sido eliminado.
    """
    logger.info(f"INFO [NotifyUserChannelDeleted] - {channel_name} eliminado de {workspace_name} por {deleted_by}")

    return create_notification(
        user_id=user.id,
        title=f"Canal eliminado: {channel_name}",
        message=f"{deleted_by} ha eliminado el canal \"{channel_name}\" del workspace \"{workspace_name}\".",
        notification_type=Notification.Type.WARNING,
    )


def notify_user_mentioned(
    user: User,
    workspace_name: str,
    channel_name: str,
    message_preview: str,
    workspace_id: UUID,
    channel_id: UUID,
    mentioned_by: str,
) -> Optional[Notification]:
    """
    Notifica a un usuario que ha sido mencionado en un mensaje.
    """
    logger.info(f"INFO [NotifyUserMentioned] - {user.email} mencionado por {mentioned_by} en {channel_name}")

    return create_notification(
        user_id=user.id,
        title=f"Mención en {channel_name}",
        message=f"{mentioned_by} te ha mencionado en el canal \"{channel_name}\": \"{message_preview[:50]}{'...' if len(message_preview) > 50 else ''}\"",
        notification_type=Notification.Type.INFO,
    )

def notify_user_promoted_to_admin(
    user: User,
    workspace_name: str,
    promoted_by: str,
) -> Optional[Notification]:
    """
    Notifica a un usuario que ha sido ascendido a ADMIN.
    """
    logger.info(f"INFO [NotifyUserPromoted] - {user.email} ascendido a admin en {workspace_name} por {promoted_by}")

    return create_notification(
        user_id=user.id,
        title=f"Has sido ascendido a ADMIN en \"{workspace_name}\"",
        message=f"{promoted_by} te ha ascendido a administrador del workspace \"{workspace_name}\".",
        notification_type=Notification.Type.SUCCESS,  # O INFO si prefieres
    )

def notify_user_reverted_to_member(
    user: User,
    workspace_name: str,
    reverted_by: str,
) -> Optional[Notification]:
    """
    Notifica a un usuario que ha sido descendido de ADMIN a MEMBER.
    """
    logger.info(f"INFO [NotifyUserReverted] - {user.email} descendido a member en {workspace_name} por {reverted_by}")

    return create_notification(
        user_id=user.id,
        title=f"Has sido descendido a MEMBER en \"{workspace_name}\"",
        message=f"{reverted_by} te ha descendido a miembro del workspace \"{workspace_name}\".",
        notification_type=Notification.Type.WARNING,
    )

@transaction.atomic
def invite_member_to_workspace(
    *,
    workspace_id: UUID,
    invited_by: User,
    email: str,
    role: str = WorkspaceMember.Role.MEMBER,
) -> WorkspaceMember:
    """
    Invitar a un usuario a un workspace.
    
    Responsabilidades:
    - Verificar que el usuario que invita sea owner o admin
    - Buscar al usuario por email
    - Verificar que no sea ya miembro
    - Crear la membresía
    - Enviar notificación al usuario invitado
    - Invalidar cache
    """
    logger.info("=" * 60)
    logger.info("INICIO [InviteMember] - Invitando miembro al workspace")
    logger.info(f"Workspace ID: {workspace_id}")
    logger.info(f"Invitado por: {invited_by.email} (ID: {invited_by.id})")
    logger.info(f"Email invitado: {email}")
    logger.info(f"Rol: {role}")
    logger.info("=" * 60)

    # 1. Obtener workspace
    workspace = get_workspace_by_id(workspace_id=workspace_id)

    # 2. Verificar permisos del que invita (owner o admin)
    if not _can_manage_workspace(user=invited_by, workspace=workspace):
        logger.warning(f"WARNING [InviteMember] - Usuario {invited_by.email} no tiene permisos")
        raise PermissionDeniedError("No tienes permiso para invitar miembros")

    # 3. Buscar al usuario por email
    from apps.accounts.selectors import get_user_by_email
    user_to_invite = get_user_by_email(email=email, use_cache=False)
    
    if not user_to_invite:
        logger.warning(f"WARNING [InviteMember] - Usuario no encontrado: {email}")
        raise ValidationError(f"No existe un usuario con el email {email}")

    # 4. Verificar que no sea ya miembro
    if WorkspaceMember.objects.filter(workspace=workspace, user=user_to_invite).exists():
        logger.warning(f"WARNING [InviteMember] - Usuario {email} ya es miembro")
        raise ValidationError(f"El usuario {email} ya es miembro de este workspace")

    # 5. Verificar que no sea el owner (el owner ya es miembro)
    if user_to_invite.id == workspace.owner_id:
        logger.warning(f"WARNING [InviteMember] - Usuario {email} es el owner")
        raise ValidationError("El usuario ya es el owner del workspace")

    try:
        # 6. Crear la membresía
        logger.info("PROCESO [InviteMember] - Creando membresía")
        member = WorkspaceMember.objects.create(
            workspace=workspace,
            user=user_to_invite,
            role=role,
        )

        # 7. Invalidar cache
        logger.info("PROCESO [InviteMember] - Invalidando cache")
        invalidate_workspace_cache(workspace_id=workspace.id)
        invalidate_user_workspaces_cache(user_id=user_to_invite.id)

        # 8. Enviar notificación de invitación
        try:
            from apps.notifications.services import notify_workspace_invite
            logger.info("PROCESO [InviteMember] - Enviando notificación de invitación")
            notification = notify_workspace_invite(
                invited_user=user_to_invite,
                invited_by=invited_by,
                workspace_name=workspace.name,
                workspace_id=workspace.id,
                role=role,
            )
            logger.info(f"✅ Notificación creada: {notification.id} para {user_to_invite.email}")
        except Exception as e:
            logger.error(f"❌ Error al enviar notificación de invitación: {e}")

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [InviteMember] - Usuario {email} invitado al workspace {workspace.name}")
        logger.info("=" * 60)

        return member

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [InviteMember] - Error al invitar a {email}")
        logger.error(f"ERROR [InviteMember] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        raise


def notify_workspace_invite(
    *,
    invited_user,
    invited_by,
    workspace_name: str,
    workspace_id,
    membership_id,
    role: str,
) -> Notification:
    """
    Notificar a un usuario que ha sido invitado a un workspace.
    Guarda los datos en el mensaje como JSON para que el frontend los extraiga.
    """
    inviter_name = invited_by.username or invited_by.email
    
    role_display = {
        'admin': 'Administrador',
        'member': 'Miembro',
        'owner': 'Propietario',
    }.get(role, 'Miembro')
    
    title = f"📨 Te han invitado a {workspace_name}"
    
    
    message_data = {
        'text': f"El owner {inviter_name} del workspace {workspace_name} te ha invitado a unirte como {role_display}.\n\n📌 ¿Aceptas o rechazas la invitación?",
        'membership_id': str(membership_id),
        'workspace_id': str(workspace_id),
        'workspace_name': workspace_name,
        'role': role,
        'inviter_name': inviter_name,
        'type': 'workspace_invite'
    }
    
    message = json.dumps(message_data)
    
    return create_notification(
        user_id=invited_user.id,
        title=title,
        message=message, 
        notification_type=Notification.Type.INFO,
    )

def notify_user_left_workspace_to_admins(
    *,
    user_left: User,
    workspace: Workspace,
    workspace_id: UUID,
) -> None:
    """
    Notificar a los Owners y Admins que un usuario abandonó el workspace.
    
    Args:
        user_left: Usuario que abandonó el workspace
        workspace: Workspace que fue abandonado
        workspace_id: UUID del workspace
    """
    logger.info(f"INFO [NotifyUserLeftToAdmins] - {user_left.email} abandonó {workspace.name}")
    
    # Obtener el nombre del usuario que abandonó
    user_name = user_left.username or user_left.email
    
    # Buscar todos los Owners y Admins del workspace (excluyendo al usuario que se fue)
    admins_and_owners = WorkspaceMember.objects.filter(
        workspace=workspace,
        role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]
    ).exclude(
        user=user_left
    ).select_related('user')
    
    if not admins_and_owners.exists():
        logger.info(f"ℹ️ No hay Owners o Admins para notificar en {workspace.name}")
        return
    
    title = f"Usuario abandonó el workspace"
    
    # 🔥 DATOS PARA EL ICONO Y LA NOTIFICACIÓN
    message_data = {
        'text': (
            f"El usuario {user_name} ha abandonado el workspace {workspace.name}.\n\n"
            f"El equipo ha perdido un miembro."
        ),
        'workspace_id': str(workspace_id),
        'workspace_name': workspace.name,
        'user_left_id': str(user_left.id),
        'user_left_name': user_name,
        'type': 'user_left_workspace',
        'action': 'abandono'
    }
    
    message = json.dumps(message_data)
    
    # Crear notificación para cada Admin y Owner
    created_count = 0
    for member in admins_and_owners:
        try:
            # Verificar preferencias del usuario
            preferences = get_user_preferences(user_id=member.user.id)
            if not preferences.in_app_enabled:
                continue
            
            notification = Notification.objects.create(
                user=member.user,
                title=title,
                message=message,
                notification_type=Notification.Type.INFO,
            )
            created_count += 1
            logger.info(f"✅ Notificación creada para {member.user.email}: {notification.id}")
        except Exception as e:
            logger.error(f"❌ Error al crear notificación para {member.user.email}: {e}")
    
    logger.info(f"✅ {created_count} notificaciones enviadas a Owners y Admins de {workspace.name}")