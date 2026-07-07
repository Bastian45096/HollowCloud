# apps/chat/selectors.py

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Count, Prefetch

from .models import Workspace, WorkspaceMember, Channel, Message, MessageAttachment
from apps.accounts.models import User
import django.db.models as models  


logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTES DE CACHE
# ============================================================

CACHE_WORKSPACE_TTL = 3600  # 1 hora
CACHE_CHANNEL_TTL = 3600
CACHE_USER_WORKSPACES_TTL = 1800  # 30 minutos
CACHE_PREFIX = "chat"


def _get_cache_key(prefix: str, identifier: str) -> str:
    """Generar clave de cache"""
    return f"{CACHE_PREFIX}:{prefix}:{identifier}"


# ============================================================
# SELECTORS: WORKSPACE
# ============================================================

def get_workspace_by_id(*, workspace_id: UUID, use_cache: bool = True) -> Workspace:
    """
    Obtener un workspace por su ID con cache.
    """
    logger.info("[GET Workspace] Buscando workspace_id=%s", workspace_id)

    if not workspace_id:
        logger.warning("[GET Workspace] Workspace ID vacío")
        raise ValidationError("Workspace ID es requerido")

    try:
        if use_cache:
            cache_key = _get_cache_key("workspace", str(workspace_id))
            workspace_data = cache.get(cache_key)
            if workspace_data:
                logger.info("[GET Workspace] Encontrado en cache: %s", workspace_id)
                return workspace_data

        workspace = (
            Workspace.objects
            .select_related('owner')
            .prefetch_related(
                Prefetch('memberships', queryset=WorkspaceMember.objects.select_related('user'))
            )
            .filter(id=workspace_id)
            .first()
        )

        if workspace is None:
            logger.warning("[GET Workspace] No encontrado: %s", workspace_id)
            raise ValidationError("Workspace no encontrado")

        if use_cache:
            cache_key = _get_cache_key("workspace", str(workspace_id))
            cache.set(cache_key, workspace, CACHE_WORKSPACE_TTL)

        logger.info("[GET Workspace] Encontrado: %s", workspace_id)
        return workspace

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[GET Workspace] Error: %s", str(exc), exc_info=True)
        raise


def get_workspace_by_slug(*, slug: str, use_cache: bool = True) -> Workspace:
    """
    Obtener un workspace por su slug.
    """
    logger.info("[GET Workspace] Buscando slug=%s", slug)

    if not slug:
        logger.warning("[GET Workspace] Slug vacío")
        raise ValidationError("Slug es requerido")

    try:
        if use_cache:
            cache_key = _get_cache_key("workspace_slug", slug)
            workspace_id = cache.get(cache_key)
            if workspace_id:
                logger.info("[GET Workspace] Slug encontrado en cache: %s", slug)
                return get_workspace_by_id(workspace_id=workspace_id, use_cache=True)

        workspace = (
            Workspace.objects
            .select_related('owner')
            .prefetch_related('memberships')
            .filter(slug=slug)
            .first()
        )

        if workspace is None:
            logger.warning("[GET Workspace] No encontrado slug=%s", slug)
            raise ValidationError("Workspace no encontrado")

        if use_cache:
            cache_key = _get_cache_key("workspace_slug", slug)
            cache.set(cache_key, workspace.id, CACHE_WORKSPACE_TTL)

        logger.info("[GET Workspace] Encontrado: %s (ID: %s)", slug, workspace.id)
        return workspace

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[GET Workspace] Error: %s", str(exc), exc_info=True)
        raise


def get_user_workspaces(*, user: User, use_cache: bool = True) -> List[Workspace]:
    """
    Obtener todos los workspaces de un usuario.
    """
    logger.info("[GET Workspaces] Buscando para usuario: %s", user.email)

    try:
        if use_cache:
            cache_key = _get_cache_key("user_workspaces", str(user.id))
            workspace_ids = cache.get(cache_key)
            if workspace_ids:
                logger.info("[GET Workspaces] Encontrado en cache: %d workspaces", len(workspace_ids))
                workspaces = (
                    Workspace.objects
                    .select_related('owner')
                    .filter(id__in=workspace_ids)
                    .order_by('name')
                )
                return list(workspaces)

        workspaces = (
            Workspace.objects
            .select_related('owner')
            .filter(
                Q(owner=user) | Q(memberships__user=user)
            )
            .distinct()
            .order_by('name')
        )

        if use_cache:
            workspace_ids = [str(w.id) for w in workspaces]
            cache_key = _get_cache_key("user_workspaces", str(user.id))
            cache.set(cache_key, workspace_ids, CACHE_USER_WORKSPACES_TTL)

        logger.info("[GET Workspaces] Encontrados: %d workspaces", workspaces.count())
        return list(workspaces)

    except Exception as exc:
        logger.error("[GET Workspaces] Error: %s", str(exc), exc_info=True)
        raise


def get_workspace_members(
    *,
    workspace_id: UUID,
    limit: int = 100,
    offset: int = 0,
    include_pending: bool = False,  
) -> Dict[str, Any]:
    """
    Obtener miembros de un workspace con paginación.
    
    Args:
        workspace_id: UUID del workspace
        limit: Límite de resultados (por defecto 100)
        offset: Offset para paginación (por defecto 0)
        include_pending: Si es True, incluye invitaciones pendientes (por defecto False)
    
    Returns:
        Dict con miembros y metadata
    """
    logger.info("[GET Members] Buscando para workspace: %s", workspace_id)

    try:
        queryset = (
            WorkspaceMember.objects
            .filter(workspace_id=workspace_id)
            .select_related('user')
            .order_by('role', 'user__email')
        )

       
        if not include_pending:
            queryset = queryset.filter(status=WorkspaceMember.Status.ACTIVE)
            logger.info("[GET Members] Filtrando solo miembros ACTIVOS")

        total = queryset.count()
        members = list(queryset[offset:offset + limit])

        logger.info("[GET Members] Encontrados: %d (total: %d)", len(members), total)

        return {
            "members": members,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as exc:
        logger.error("[GET Members] Error: %s", str(exc), exc_info=True)
        raise


def is_workspace_member(
    *,
    workspace_id: UUID,
    user: User,
    include_pending: bool = False,  
) -> bool:
    """
    Verificar si un usuario es miembro de un workspace.
    """
    logger.info("[GET Member] Verificando user=%s en workspace=%s", user.id, workspace_id)

    try:
        queryset = WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user=user
        )
        
        
        if not include_pending:
            queryset = queryset.filter(status=WorkspaceMember.Status.ACTIVE)
        
        return queryset.exists()

    except Exception as exc:
        logger.error("[GET Member] Error: %s", str(exc), exc_info=True)
        return False


def get_workspace_member(
    *,
    workspace_id: UUID,
    user: User,
) -> Optional[WorkspaceMember]:
    """
    Obtener la membresía de un usuario en un workspace.
    """
    logger.info("[GET Member] Obteniendo membresía de user=%s en workspace=%s", user.id, workspace_id)

    try:
        membership = WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user=user
        ).first()
        return membership

    except Exception as exc:
        logger.error("[GET Member] Error: %s", str(exc), exc_info=True)
        return None

def search_workspaces(
    *,
    query: str,
    user: User,
    limit: int = 20,
) -> List[Workspace]:
    """
    Buscar workspaces públicos por nombre o slug.
    Excluye workspaces donde el usuario ya es miembro.
    """
    logger.info(f"[Search Workspaces] Buscando: {query}")

    try:
        if not query or len(query.strip()) < 2:
            return []

        # Obtener IDs de workspaces donde el usuario es miembro
        user_workspace_ids = WorkspaceMember.objects.filter(
            user=user
        ).values_list('workspace_id', flat=True)

        # Buscar workspaces por nombre o slug
        workspaces = Workspace.objects.filter(
            models.Q(name__icontains=query) |
            models.Q(slug__icontains=query)
        ).exclude(
            id__in=user_workspace_ids
        ).exclude(
            owner=user  # Excluir los que el usuario ya es owner (ya es miembro)
        ).select_related('owner')[:limit]

        logger.info(f"[Search Workspaces] Encontrados: {workspaces.count()}")
        return list(workspaces)

    except Exception as exc:
        logger.error(f"[Search Workspaces] Error: {str(exc)}", exc_info=True)
        return []

# ============================================================
# SELECTORS: CHANNEL
# ============================================================

def get_channel_by_id(*, channel_id: UUID, use_cache: bool = True) -> Channel:
    """
    Obtener un canal por su ID con cache.
    """
    logger.info("[GET Channel] Buscando channel_id=%s", channel_id)

    if not channel_id:
        logger.warning("[GET Channel] Channel ID vacío")
        raise ValidationError("Channel ID es requerido")

    try:
        if use_cache:
            cache_key = _get_cache_key("channel", str(channel_id))
            channel_data = cache.get(cache_key)
            if channel_data:
                logger.info("[GET Channel] Encontrado en cache: %s", channel_id)
                return channel_data

        channel = (
            Channel.objects
            .select_related('workspace', 'workspace__owner')
            .filter(id=channel_id)
            .first()
        )

        if channel is None:
            logger.warning("[GET Channel] No encontrado: %s", channel_id)
            raise ValidationError("Canal no encontrado")

        if use_cache:
            cache_key = _get_cache_key("channel", str(channel_id))
            cache.set(cache_key, channel, CACHE_CHANNEL_TTL)

        return channel

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[GET Channel] Error: %s", str(exc), exc_info=True)
        raise


def get_channel_by_slug(*, workspace_id: UUID, slug: str) -> Channel:
    """
    Obtener un canal por su slug dentro de un workspace.
    """
    logger.info("[GET Channel] Buscando slug=%s en workspace=%s", slug, workspace_id)

    if not slug:
        raise ValidationError("Slug es requerido")

    try:
        channel = (
            Channel.objects
            .select_related('workspace')
            .filter(workspace_id=workspace_id, slug=slug)
            .first()
        )

        if channel is None:
            logger.warning("[GET Channel] No encontrado slug=%s", slug)
            raise ValidationError("Canal no encontrado")

        return channel

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[GET Channel] Error: %s", str(exc), exc_info=True)
        raise


def get_workspace_channels(*, workspace_id: UUID) -> List[Channel]:
    """
    Obtener todos los canales de un workspace.
    """
    logger.info("[GET Channels] Buscando para workspace: %s", workspace_id)

    try:
        channels = (
            Channel.objects
            .filter(workspace_id=workspace_id)
            .select_related('workspace')
            .order_by('name')
        )

        logger.info("[GET Channels] Encontrados: %d canales", channels.count())
        return list(channels)

    except Exception as exc:
        logger.error("[GET Channels] Error: %s", str(exc), exc_info=True)
        raise


# ============================================================
# SELECTORS: MESSAGE
# ============================================================

def get_channel_messages(
    *,
    channel_id: UUID,
    limit: int = 50,
    offset: int = 0,
    include_attachments: bool = True,
) -> Dict[str, Any]:
    """
    Obtener mensajes de un canal con paginación.
    """
    logger.info("[GET Messages] Buscando para channel: %s", channel_id)

    try:
        queryset = (
            Message.objects
            .filter(channel_id=channel_id)
            .select_related('author')
            .order_by('created_at') 
        )

        if include_attachments:
            queryset = queryset.prefetch_related('attachments')

        total = queryset.count()
        messages = list(queryset[offset:offset + limit])

        logger.info("[GET Messages] Encontrados: %d (total: %d)", len(messages), total)

        return {
            "messages": messages,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as exc:
        logger.error("[GET Messages] Error: %s", str(exc), exc_info=True)
        raise


def get_message_by_id(*, message_id: UUID) -> Message:
    """
    Obtener un mensaje por su ID.
    """
    logger.info("[GET Message] Buscando message_id=%s", message_id)

    try:
        message = (
            Message.objects
            .select_related('author', 'channel', 'channel__workspace')
            .prefetch_related('attachments')
            .filter(id=message_id)
            .first()
        )

        if message is None:
            logger.warning("[GET Message] No encontrado: %s", message_id)
            raise ValidationError("Mensaje no encontrado")

        return message

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[GET Message] Error: %s", str(exc), exc_info=True)
        raise


def get_messages_by_user(
    *,
    user: User,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Obtener mensajes de un usuario en todos los canales.
    """
    logger.info("[GET Messages] Buscando mensajes de usuario: %s", user.email)

    try:
        queryset = (
            Message.objects
            .filter(author=user)
            .select_related('channel', 'channel__workspace')
            .order_by('-created_at')
        )

        total = queryset.count()
        messages = list(queryset[offset:offset + limit])

        logger.info("[GET Messages] Encontrados: %d (total: %d)", len(messages), total)

        return {
            "messages": messages,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as exc:
        logger.error("[GET Messages] Error: %s", str(exc), exc_info=True)
        raise


# ============================================================
# SELECTORS: ATTACHMENT
# ============================================================

def get_message_attachments(*, message_id: UUID) -> List[MessageAttachment]:
    """
    Obtener todos los adjuntos de un mensaje.
    """
    logger.info("[GET Attachments] Buscando adjuntos para message: %s", message_id)

    try:
        attachments = (
            MessageAttachment.objects
            .filter(message_id=message_id)
            .order_by('-created_at')
        )

        logger.info("[GET Attachments] Encontrados: %d", attachments.count())
        return list(attachments)

    except Exception as exc:
        logger.error("[GET Attachments] Error: %s", str(exc), exc_info=True)
        raise


def get_attachment_by_id(*, attachment_id: UUID) -> Optional[MessageAttachment]:
    """
    Obtener un adjunto por su ID.
    """
    logger.info("[GET Attachment] Buscando attachment_id=%s", attachment_id)

    try:
        attachment = (
            MessageAttachment.objects
            .select_related('message', 'message__author')
            .filter(id=attachment_id)
            .first()
        )

        return attachment

    except Exception as exc:
        logger.error("[GET Attachment] Error: %s", str(exc), exc_info=True)
        return None




# ============================================================
# FUNCIONES PARA INVALIDAR CACHE
# ============================================================

def invalidate_workspace_cache(*, workspace_id: UUID) -> None:
    """Invalidar cache de un workspace"""
    cache.delete(_get_cache_key("workspace", str(workspace_id)))
    logger.info("[Cache] Workspace invalidado: %s", workspace_id)


def invalidate_channel_cache(*, channel_id: UUID) -> None:
    """Invalidar cache de un canal"""
    cache.delete(_get_cache_key("channel", str(channel_id)))
    logger.info("[Cache] Channel invalidado: %s", channel_id)


def invalidate_user_workspaces_cache(*, user_id: UUID) -> None:
    """Invalidar cache de workspaces de un usuario"""
    cache.delete(_get_cache_key("user_workspaces", str(user_id)))
    logger.info("[Cache] User workspaces invalidado: %s", user_id)


def invalidate_all_chat_cache(*, workspace_id: UUID, user_id: UUID) -> None:
    """Invalidar todas las caches relacionadas con chat"""
    invalidate_workspace_cache(workspace_id=workspace_id)
    invalidate_user_workspaces_cache(user_id=user_id)
    logger.info("[Cache] Todas las caches de chat invalidadas")



def invalidate_user_workspaces_cache(*, user_id: UUID) -> None:
    """Invalidar cache de workspaces de un usuario"""
    cache_key = _get_cache_key("user_workspaces", str(user_id))
    cache.delete(cache_key)
    logger.info("[Cache] User workspaces invalidado: %s", user_id)

def get_user_by_email_from_invite(*, email: str) -> Optional[User]:
    """
    Obtener un usuario por email para invitación.
    """
    from apps.accounts.models import User
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        return None