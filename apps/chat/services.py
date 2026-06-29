# apps/chat/services.py

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.common.exceptions import PermissionDeniedError, NotFoundError

from .models import Workspace, WorkspaceMember, Channel, Message, MessageAttachment
from .selectors import (
    get_workspace_by_id,
    get_channel_by_id,
    get_message_by_id,
    is_workspace_member,
    invalidate_workspace_cache,
    invalidate_channel_cache,
    invalidate_user_workspaces_cache,
)

logger = logging.getLogger(__name__)
from django.utils.text import slugify


# ============================================================
# FUNCIONES AUXILIARES PRIVADAS
# ============================================================

def _can_manage_workspace(*, user: User, workspace: Workspace) -> bool:
    """
    Verificar si un usuario puede gestionar un workspace.
    """
    # Owner siempre puede
    if workspace.owner_id == user.id:
        return True

    # Verificar si es admin
    membership = WorkspaceMember.objects.filter(
        workspace=workspace,
        user=user,
        role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]
    ).exists()

    return membership


def _check_membership(*, workspace_id: UUID, user: User) -> None:
    """
    Verificar que un usuario sea miembro del workspace.
    """
    if not is_workspace_member(workspace_id=workspace_id, user=user):
        raise PermissionDeniedError("No eres miembro de este workspace")


# ============================================================
# WORKSPACE SERVICES
# ============================================================

# apps/chat/services.py

@transaction.atomic
def join_workspace(
    *,
    workspace_id: UUID,
    user: User,
) -> WorkspaceMember:
    """
    Unir a un usuario a un workspace.
    """
    logger.info("[Join Workspace] Uniendo usuario %s al workspace %s", user.email, workspace_id)

    workspace = get_workspace_by_id(workspace_id=workspace_id)

    if WorkspaceMember.objects.filter(workspace=workspace, user=user).exists():
        raise ValidationError("Ya eres miembro de este workspace")

    if workspace.owner_id == user.id:
        raise ValidationError("Eres el owner de este workspace")

    try:
        member = WorkspaceMember.objects.create(
            workspace=workspace,
            user=user,
            role=WorkspaceMember.Role.MEMBER,
        )

        invalidate_workspace_cache(workspace_id=workspace.id)

        logger.info("[Join Workspace] Usuario %s unido al workspace %s", user.email, workspace.id)
        return member

    except Exception as exc:
        logger.error("[Join Workspace] Error: %s", str(exc), exc_info=True)
        raise

# apps/chat/services.py

@transaction.atomic
def create_workspace(
    *,
    name: str,
    owner: User,
    slug: str = None,
    description: str = '',
) -> Workspace:
    """
    Crear un nuevo workspace.
    """
    logger.info("[Create Workspace] Creando workspace: %s por %s", name, owner.email)

    if not name or not name.strip():
        raise ValidationError("El nombre del workspace es requerido")

    if not slug or not slug.strip():
        slug = slugify(name)
        logger.info(f"[Create Workspace] Slug generado automáticamente: {slug}")

    if Workspace.objects.filter(slug=slug).exists():
        raise ValidationError(f"Ya existe un workspace con el slug '{slug}'")

    try:
        workspace = Workspace.objects.create(
            name=name.strip(),
            slug=slug.strip().lower(),
            owner=owner,
            description=description.strip() if description else '',
        )

        WorkspaceMember.objects.create(
            workspace=workspace,
            user=owner,
            role=WorkspaceMember.Role.OWNER,
        )

       
        invalidate_workspace_cache(workspace_id=workspace.id)
        
        
        invalidate_user_workspaces_cache(user_id=owner.id)

        logger.info("[Create Workspace] Workspace creado: %s (ID: %s)", workspace.name, workspace.id)
        return workspace

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[Create Workspace] Error: %s", str(exc), exc_info=True)
        raise



@transaction.atomic
def update_workspace(
    *,
    workspace_id: UUID,
    user: User,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Workspace:
    """
    Actualizar un workspace.
    
    Responsabilidades:
    - Validar que el usuario sea owner o admin del workspace
    - Actualizar los campos permitidos
    - Invalidar cache
    """
    logger.info("[Update Workspace] Actualizando workspace: %s por %s", workspace_id, user.email)

    # Obtener workspace
    workspace = get_workspace_by_id(workspace_id=workspace_id)

    # Verificar permisos (solo owner o admin pueden editar)
    if not _can_manage_workspace(user=user, workspace=workspace):
        raise PermissionDeniedError("No tienes permiso para editar este workspace")

    try:
        if name is not None:
            if not name.strip():
                raise ValidationError("El nombre no puede estar vacío")
            workspace.name = name.strip()
        
        if description is not None:
            workspace.description = description.strip() if description else ''

        workspace.save()

        # Invalidar cache
        invalidate_workspace_cache(workspace_id=workspace.id)

        logger.info("[Update Workspace] Workspace actualizado: %s", workspace.id)
        return workspace

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[Update Workspace] Error: %s", str(exc), exc_info=True)
        raise


@transaction.atomic
def delete_workspace(
    *,
    workspace_id: UUID,
    user: User,
) -> None:
    """
    Eliminar un workspace (solo el owner puede hacerlo).
    """
    logger.info("[Delete Workspace] Eliminando workspace: %s por %s", workspace_id, user.email)

    workspace = get_workspace_by_id(workspace_id=workspace_id)

    # Solo el owner puede eliminar el workspace
    if workspace.owner_id != user.id:
        raise PermissionDeniedError("Solo el owner puede eliminar este workspace")

    try:
        # Eliminar cache
        invalidate_workspace_cache(workspace_id=workspace.id)
        
        # Eliminar workspace (cascada elimina miembros, canales y mensajes)
        workspace.delete()

        logger.info("[Delete Workspace] Workspace eliminado: %s", workspace_id)

    except Exception as exc:
        logger.error("[Delete Workspace] Error: %s", str(exc), exc_info=True)
        raise


@transaction.atomic
def add_member_to_workspace(
    *,
    workspace_id: UUID,
    user_to_add: User,
    added_by: User,
    role: str = WorkspaceMember.Role.MEMBER,
) -> WorkspaceMember:
    """
    Agregar un miembro a un workspace.
    """
    logger.info("[Add Member] Agregando %s a workspace %s por %s", 
                user_to_add.email, workspace_id, added_by.email)

    workspace = get_workspace_by_id(workspace_id=workspace_id)

    # Verificar permisos (solo owner o admin pueden agregar miembros)
    if not _can_manage_workspace(user=added_by, workspace=workspace):
        raise PermissionDeniedError("No tienes permiso para agregar miembros")

    # Verificar que el usuario no sea ya miembro
    if WorkspaceMember.objects.filter(workspace=workspace, user=user_to_add).exists():
        raise ValidationError(f"El usuario {user_to_add.email} ya es miembro de este workspace")

    # Verificar que no se agregue a sí mismo (si ya es owner)
    if user_to_add.id == workspace.owner_id:
        raise ValidationError("El owner ya es miembro del workspace")

    try:
        member = WorkspaceMember.objects.create(
            workspace=workspace,
            user=user_to_add,
            role=role,
        )

        # Invalidar cache del workspace
        invalidate_workspace_cache(workspace_id=workspace.id)

        logger.info("[Add Member] Miembro agregado: %s con rol %s", user_to_add.email, role)
        return member

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[Add Member] Error: %s", str(exc), exc_info=True)
        raise


@transaction.atomic
def remove_member_from_workspace(
    *,
    workspace_id: UUID,
    user_to_remove: User,
    removed_by: User,
) -> None:
    """
    Remover un miembro de un workspace.
    """
    logger.info("[Remove Member] Removiendo %s de workspace %s por %s",
                user_to_remove.email, workspace_id, removed_by.email)

    workspace = get_workspace_by_id(workspace_id=workspace_id)

    # Verificar permisos
    if not _can_manage_workspace(user=removed_by, workspace=workspace):
        raise PermissionDeniedError("No tienes permiso para remover miembros")

    # No se puede remover al owner
    if workspace.owner_id == user_to_remove.id:
        raise ValidationError("No se puede remover al owner del workspace")

    # No se puede remover a sí mismo (si no es admin)
    if user_to_remove.id == removed_by.id and not _can_manage_workspace(user=removed_by, workspace=workspace):
        raise PermissionDeniedError("No puedes removerte a ti mismo si no eres admin")

    try:
        deleted_count, _ = WorkspaceMember.objects.filter(
            workspace=workspace,
            user=user_to_remove
        ).delete()
        
        if deleted_count == 0:
            raise ValidationError("El usuario no es miembro de este workspace")

        # Invalidar cache del workspace
        invalidate_workspace_cache(workspace_id=workspace.id)

        logger.info("[Remove Member] Miembro removido: %s", user_to_remove.email)

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[Remove Member] Error: %s", str(exc), exc_info=True)
        raise


@transaction.atomic
def update_member_role(
    *,
    workspace_id: UUID,
    user_to_update: User,
    updated_by: User,
    role: str,
) -> WorkspaceMember:
    """
    Actualizar el rol de un miembro en un workspace.
    """
    logger.info("[Update Member] Actualizando rol de %s en workspace %s por %s",
                user_to_update.email, workspace_id, updated_by.email)

    workspace = get_workspace_by_id(workspace_id=workspace_id)

    # Verificar permisos
    if not _can_manage_workspace(user=updated_by, workspace=workspace):
        raise PermissionDeniedError("No tienes permiso para cambiar roles")

    # No se puede cambiar el rol del owner
    if workspace.owner_id == user_to_update.id:
        raise ValidationError("No se puede cambiar el rol del owner")

    # Verificar que el usuario sea miembro
    membership = WorkspaceMember.objects.filter(
        workspace=workspace,
        user=user_to_update
    ).first()

    if not membership:
        raise ValidationError("El usuario no es miembro de este workspace")

    try:
        membership.role = role
        membership.save()

        # Invalidar cache del workspace
        invalidate_workspace_cache(workspace_id=workspace.id)

        logger.info("[Update Member] Rol actualizado de %s a %s", user_to_update.email, role)
        return membership

    except Exception as exc:
        logger.error("[Update Member] Error: %s", str(exc), exc_info=True)
        raise


# ============================================================
# CHANNEL SERVICES
# ============================================================

@transaction.atomic
def create_channel(
    *,
    workspace_id: UUID,
    name: str,
    created_by: User,
    slug: str = None,  
    channel_type: str = Channel.Type.TEXT,
    description: str = '',
) -> Channel:
    """
    Crear un nuevo canal en un workspace.
    """
    logger.info("[Create Channel] Creando canal %s en workspace %s por %s",
                name, workspace_id, created_by.email)

    workspace = get_workspace_by_id(workspace_id=workspace_id)

    # Verificar permisos
    if not _can_manage_workspace(user=created_by, workspace=workspace):
        raise PermissionDeniedError("No tienes permiso para crear canales en este workspace")

    if not name or not name.strip():
        raise ValidationError("El nombre del canal es requerido")

    
    if not slug or not slug.strip():
        slug = slugify(name)
        logger.info(f"[Create Channel] Slug generado automáticamente: {slug}")

    # Verificar slug único en el workspace
    if Channel.objects.filter(workspace=workspace, slug=slug).exists():
        raise ValidationError(f"Ya existe un canal con el slug '{slug}' en este workspace")

    try:
        channel = Channel.objects.create(
            workspace=workspace,
            name=name.strip(),
            slug=slug.strip().lower(),
            channel_type=channel_type,
            description=description.strip() if description else '',
        )

        # Invalidar cache del workspace
        invalidate_workspace_cache(workspace_id=workspace.id)

        logger.info("[Create Channel] Canal creado: %s (ID: %s)", channel.name, channel.id)
        return channel

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[Create Channel] Error: %s", str(exc), exc_info=True)
        raise


@transaction.atomic
def update_channel(
    *,
    channel_id: UUID,
    user: User,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Channel:
    """
    Actualizar un canal.
    """
    logger.info("[Update Channel] Actualizando canal: %s por %s", channel_id, user.email)

    channel = get_channel_by_id(channel_id=channel_id)

    # Verificar permisos
    if not _can_manage_workspace(user=user, workspace=channel.workspace):
        raise PermissionDeniedError("No tienes permiso para editar este canal")

    try:
        if name is not None:
            if not name.strip():
                raise ValidationError("El nombre no puede estar vacío")
            channel.name = name.strip()
        
        if description is not None:
            channel.description = description.strip() if description else ''

        channel.save()

        # Invalidar cache
        invalidate_channel_cache(channel_id=channel.id)
        invalidate_workspace_cache(workspace_id=channel.workspace_id)

        logger.info("[Update Channel] Canal actualizado: %s", channel.id)
        return channel

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[Update Channel] Error: %s", str(exc), exc_info=True)
        raise


@transaction.atomic
def delete_channel(
    *,
    channel_id: UUID,
    user: User,
) -> None:
    """
    Eliminar un canal.
    """
    logger.info("[Delete Channel] Eliminando canal: %s por %s", channel_id, user.email)

    channel = get_channel_by_id(channel_id=channel_id)

    # Verificar permisos
    if not _can_manage_workspace(user=user, workspace=channel.workspace):
        raise PermissionDeniedError("No tienes permiso para eliminar este canal")

    try:
        # Invalidar cache
        invalidate_channel_cache(channel_id=channel.id)
        invalidate_workspace_cache(workspace_id=channel.workspace_id)

        channel.delete()
        logger.info("[Delete Channel] Canal eliminado: %s", channel_id)

    except Exception as exc:
        logger.error("[Delete Channel] Error: %s", str(exc), exc_info=True)
        raise


# ============================================================
# MESSAGE SERVICES
# ============================================================

# apps/chat/services.py

# apps/chat/services.py

@transaction.atomic
def send_message(
    *,
    channel_id: UUID,
    author: User,
    content: str,
) -> Message:
    """
    Enviar un mensaje en un canal.
    """
    logger.info("[Send Message] Enviando mensaje de %s en canal %s", 
                author.email, channel_id)

    channel = get_channel_by_id(channel_id=channel_id)

    # Verificar que el usuario sea miembro del workspace
    if not is_workspace_member(workspace_id=channel.workspace_id, user=author):
        raise PermissionDeniedError("No eres miembro de este workspace")

    # PERMITIR contenido vacío (para archivos)
    # Solo validar longitud si hay contenido
    if content and len(content.strip()) > 10000:
        raise ValidationError("El mensaje no puede exceder los 10,000 caracteres")

    try:
       
        final_content = content.strip() if content else ''
        
        message = Message.objects.create(
            channel=channel,
            author=author,
            content=final_content,
        )

        logger.info("[Send Message] Mensaje enviado: %s", message.id)
        return message

    except Exception as exc:
        logger.error("[Send Message] Error: %s", str(exc), exc_info=True)
        raise


@transaction.atomic
def edit_message(
    *,
    message_id: UUID,
    user: User,
    new_content: str,
) -> Message:
    """
    Editar un mensaje existente.
    """
    logger.info("[Edit Message] Editando mensaje %s por %s", message_id, user.email)

    message = get_message_by_id(message_id=message_id)

    # Solo el autor puede editar su mensaje
    if message.author_id != user.id:
        raise PermissionDeniedError("No puedes editar un mensaje que no te pertenece")

    if not new_content or not new_content.strip():
        raise ValidationError("El mensaje no puede estar vacío")

    if len(new_content.strip()) > 10000:
        raise ValidationError("El mensaje no puede exceder los 10,000 caracteres")

    try:
        message.content = new_content.strip()
        message.edited_at = timezone.now()
        message.save()

        logger.info("[Edit Message] Mensaje editado: %s", message_id)
        return message

    except Exception as exc:
        logger.error("[Edit Message] Error: %s", str(exc), exc_info=True)
        raise


@transaction.atomic
def delete_message(
    *,
    message_id: UUID,
    user: User,
) -> None:
    """
    Eliminar un mensaje.
    """
    logger.info("[Delete Message] Eliminando mensaje %s por %s", message_id, user.email)

    message = get_message_by_id(message_id=message_id)

    # Solo el autor o admin pueden eliminar
    if message.author_id != user.id:
        # Verificar si el usuario es admin del workspace
        workspace = message.channel.workspace
        if not _can_manage_workspace(user=user, workspace=workspace):
            raise PermissionDeniedError("No tienes permiso para eliminar este mensaje")

    try:
        message.delete()
        logger.info("[Delete Message] Mensaje eliminado: %s", message_id)

    except Exception as exc:
        logger.error("[Delete Message] Error: %s", str(exc), exc_info=True)
        raise


# ============================================================
# ATTACHMENT SERVICES
# ============================================================

@transaction.atomic
def add_attachment_to_message(
    *,
    message_id: UUID,
    user: User,
    file,
    original_name: str,
    mime_type: str,
    size: int,
) -> MessageAttachment:
    """
    Agregar un archivo adjunto a un mensaje.
    """
    logger.info("[Add Attachment] Agregando adjunto a mensaje %s por %s",
                message_id, user.email)

    message = get_message_by_id(message_id=message_id)

    # Verificar que el usuario sea el autor del mensaje
    if message.author_id != user.id:
        raise PermissionDeniedError("No puedes agregar adjuntos a mensajes que no te pertenecen")

    # Validar tamaño máximo (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    if size > MAX_FILE_SIZE:
        raise ValidationError(f"El archivo no puede superar los 10MB (tamaño actual: {size / 1024 / 1024:.2f}MB)")

    try:
        attachment = MessageAttachment.objects.create(
            message=message,
            file=file,
            original_name=original_name,
            mime_type=mime_type,
            size=size,
        )

        logger.info("[Add Attachment] Adjunto agregado: %s (tamaño: %s bytes)", attachment.id, size)
        return attachment

    except Exception as exc:
        logger.error("[Add Attachment] Error: %s", str(exc), exc_info=True)
        raise


@transaction.atomic
def remove_attachment(
    *,
    attachment_id: UUID,
    user: User,
) -> None:
    """
    Eliminar un archivo adjunto de un mensaje.
    """
    logger.info("[Remove Attachment] Eliminando adjunto %s por %s", attachment_id, user.email)

    attachment = MessageAttachment.objects.select_related('message__author').filter(id=attachment_id).first()

    if not attachment:
        raise NotFoundError("Adjunto no encontrado")

    # Verificar que el usuario sea el autor del mensaje
    if attachment.message.author_id != user.id:
        # Verificar si el usuario es admin del workspace
        workspace = attachment.message.channel.workspace
        if not _can_manage_workspace(user=user, workspace=workspace):
            raise PermissionDeniedError("No tienes permiso para eliminar este adjunto")

    try:
        # Eliminar el archivo del sistema de archivos también
        attachment.file.delete()
        attachment.delete()

        logger.info("[Remove Attachment] Adjunto eliminado: %s", attachment_id)

    except Exception as exc:
        logger.error("[Remove Attachment] Error: %s", str(exc), exc_info=True)
        raise