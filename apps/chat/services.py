# apps/chat/services.py

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.utils.text import slugify

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
    description: str = "",
) -> Workspace:
    """
    Crear un nuevo workspace.
    """
    logger.info("INICIO [CreateWorkspace] - Creando workspace")
    logger.info(f"Nombre: {name}")
    logger.info(f"Owner: {owner.email}")

    try:
       
        slug = slugify(name)
        
        # Si el slug ya existe, agregar un sufijo
        base_slug = slug
        counter = 1
        while Workspace.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        workspace = Workspace.objects.create(
            name=name,
            slug=slug,
            owner=owner,
            description=description,
        )

       
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=owner,
            role=WorkspaceMember.Role.OWNER,
            status=WorkspaceMember.Status.ACTIVE,
        )

        logger.info(f" Workspace creado: {workspace.id} (slug: {workspace.slug})")
        return workspace

    except Exception as exc:
        logger.error(f"ERROR [CreateWorkspace] - Error: {str(exc)}", exc_info=True)
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
    user: User,
    role: str = WorkspaceMember.Role.MEMBER,
) -> WorkspaceMember:
    """
    Agregar un usuario a un workspace (CUANDO ACEPTA LA INVITACIÓN).
    """
    logger.info("INICIO [AddMemberToWorkspace] - Agregando miembro")
    logger.info(f"Workspace ID: {workspace_id}")
    logger.info(f"Usuario: {user.email}")

    workspace = get_workspace_by_id(workspace_id=workspace_id)

    # Verificar que no sea ya miembro
    if WorkspaceMember.objects.filter(workspace=workspace, user=user).exists():
        raise ValidationError("El usuario ya es miembro de este workspace")

    # CREAR MIEMBRO CON STATUS ACTIVE
    member = WorkspaceMember.objects.create(
        workspace=workspace,
        user=user,
        role=role,
        status=WorkspaceMember.Status.ACTIVE,  )

    logger.info(f"Miembro agregado: {member.id}")
    return member


@transaction.atomic
def remove_member_from_workspace(
    *,
    workspace_id: UUID,
    user_id: UUID,
    removed_by: User,
) -> bool:
    """
    Eliminar un miembro de un workspace (expulsar o abandonar).
    
    Args:
        workspace_id: UUID del workspace
        user_id: UUID del usuario a eliminar
        removed_by: Usuario que realiza la acción (puede ser el mismo)
    
    Returns:
        bool: True si se eliminó correctamente
    """
    logger.info("=" * 60)
    logger.info("INICIO [RemoveMember] - Eliminando miembro del workspace")
    logger.info(f"Workspace ID: {workspace_id}")
    logger.info(f"Usuario a eliminar: {user_id}")
    logger.info(f"Eliminado por: {removed_by.email}")
    logger.info("=" * 60)

    try:
        workspace = get_workspace_by_id(workspace_id=workspace_id)
        
        # Obtener la membresía del usuario a eliminar
        target_membership = WorkspaceMember.objects.filter(
            workspace=workspace,
            user_id=user_id
        ).first()
        
        if not target_membership:
            raise ValidationError("El usuario no es miembro de este workspace")
        
        # Guardar información para la notificación
        target_user = target_membership.user
        is_self_removal = str(user_id) == str(removed_by.id)
        
        # No se puede eliminar al owner
        if target_membership.role == WorkspaceMember.Role.OWNER:
            raise ValidationError("No se puede eliminar al owner del workspace")
        
        # Verificar permisos si no es auto-eliminación
        if not is_self_removal:
            remover_membership = WorkspaceMember.objects.filter(
                workspace=workspace,
                user=removed_by
            ).first()
            
            if not remover_membership or remover_membership.role not in [WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]:
                raise PermissionDeniedError("No tienes permiso para eliminar miembros")
        
        # Eliminar la membresía
        target_membership.delete()
        
        # Invalidar caches
        invalidate_workspace_cache(workspace_id=workspace.id)
        invalidate_user_workspaces_cache(user_id=user_id)
        invalidate_user_workspaces_cache(user_id=removed_by.id)
        
        # 🔥 ENVIAR NOTIFICACIÓN A OWNERS Y ADMINS (si no es auto-eliminación o siempre)
        if is_self_removal:
            # El usuario abandonó el workspace
            from apps.notifications.services import notify_user_left_workspace_to_admins
            notify_user_left_workspace_to_admins(
                user_left=target_user,
                workspace=workspace,
                workspace_id=workspace.id,
            )
            logger.info(f"✅ Notificación de abandono enviada a Owners y Admins")
        else:
            # El usuario fue expulsado (podrías tener otra notificación)
            from apps.notifications.services import notify_user_expelled_from_workspace
            notify_user_expelled_from_workspace(
                user=target_user,
                workspace_name=workspace.name,
                workspace_id=workspace.id,
                expelled_by=removed_by.username or removed_by.email,
            )
            logger.info(f"✅ Notificación de expulsión enviada a {target_user.email}")

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [RemoveMember] - Miembro eliminado del workspace")
        logger.info("=" * 60)
        
        return True

    except ValidationError as e:
        logger.warning(f"WARNING [RemoveMember] - Error de validación: {str(e)}")
        raise
    except PermissionDeniedError as e:
        logger.warning(f"WARNING [RemoveMember] - Error de permisos: {str(e)}")
        raise
    except Exception as exc:
        logger.error(f"ERROR [RemoveMember] - Error: {str(exc)}", exc_info=True)
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

@transaction.atomic
def invite_member_to_workspace(
    *,
    workspace_id: UUID,
    invited_by: User,
    email: str,
    role: str = WorkspaceMember.Role.MEMBER,
) -> WorkspaceMember:
    """
    Invitar a un usuario a un workspace (CREA MEMBRESÍA PENDIENTE)
    """
    logger.info("=" * 60)
    logger.info("INICIO [InviteMember] - Invitando miembro al workspace")
    logger.info(f"Workspace ID: {workspace_id}")
    logger.info(f"Invitado por: {invited_by.email}")
    logger.info(f"Email invitado: {email}")
    logger.info(f"Rol: {role}")
    logger.info("=" * 60)

    # 1. Obtener workspace
    workspace = get_workspace_by_id(workspace_id=workspace_id)

    # 2. Verificar permisos
    if not _can_manage_workspace(user=invited_by, workspace=workspace):
        raise PermissionDeniedError("No tienes permiso para invitar miembros")

    # 3. Buscar al usuario
    from apps.accounts.selectors import get_user_by_email
    user_to_invite = get_user_by_email(email=email, use_cache=False)
    if not user_to_invite:
        raise ValidationError(f"No existe un usuario con el email {email}")

    # 4. 🔥 VERIFICAR QUE EL USUARIO NO TENGA UNA INVITACIÓN PENDIENTE
    if WorkspaceMember.objects.filter(
        workspace=workspace,
        user=user_to_invite,
        status=WorkspaceMember.Status.PENDING
    ).exists():
        logger.warning(f"WARNING [InviteMember] - Ya existe invitación pendiente para {email}")
        raise ValidationError(f"El usuario {email} ya posee una invitación pendiente a este workspace")

    # 5. Verificar que no sea ya miembro ACTIVO
    if WorkspaceMember.objects.filter(
        workspace=workspace,
        user=user_to_invite,
        status=WorkspaceMember.Status.ACTIVE
    ).exists():
        raise ValidationError(f"El usuario {email} ya es miembro de este workspace")

    # 6. Verificar que no sea el owner
    if user_to_invite.id == workspace.owner_id:
        raise ValidationError("El usuario ya es el owner del workspace")

    # 7. CREAR NUEVA MEMBRESÍA CON STATUS PENDING
    member = WorkspaceMember.objects.create(
        workspace=workspace,
        user=user_to_invite,
        role=role,
        status=WorkspaceMember.Status.PENDING,
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(days=7),
    )

    # 8. ENVIAR NOTIFICACIÓN
    from apps.notifications.services import notify_workspace_invite
    notify_workspace_invite(
        invited_user=user_to_invite,
        invited_by=invited_by,
        workspace_name=workspace.name,
        workspace_id=workspace.id,
        membership_id=member.id,
        role=role,
    )

    logger.info(f"✅ Invitación creada: {member.id} para {email}")
    return member

@transaction.atomic
def service_leave_workspace(user: User, workspace_id: int) -> Dict[str, Any]:
    """
    Permite que un usuario (Member, Admin o Owner) abandone un workspace.
    
    Reglas de Negocio:
    1. El usuario debe ser miembro activo.
    2. CRÍTICO: Si el usuario es el ÚNICO OWNER activo, no puede abandonar.
       Debe transferir el ownership o eliminar el workspace primero.
    3. Elimina la membresía de la base de datos.
    """
    # 1. Obtener el workspace
    try:
        workspace = Workspace.objects.get(id=workspace_id)
    except Workspace.DoesNotExist:
        raise ValueError("Workspace no encontrado")

    # 2. Obtener la membresía del usuario
    try:
        membership = WorkspaceMember.objects.select_related('user').get(
            workspace=workspace, 
            user=user
        )
    except WorkspaceMember.DoesNotExist:
        # Caso idempotente: Si ya no es miembro, consideramos éxito sin acción
        return {
            'success': True,
            'message': 'Ya no eres miembro de este workspace.',
            'action_performed': False
        }

    # 3. Validación Crítica de Seguridad: Último Owner
    if membership.role == WorkspaceMember.Role.OWNER:
        # Contar cuántos owners activos existen en este workspace
        owner_count = WorkspaceMember.objects.filter(
            workspace=workspace,
            role=WorkspaceMember.Role.OWNER,
            status=WorkspaceMember.Status.ACTIVE
        ).count()

        # Si solo hay 1 (el actual), bloquear la salida
        if owner_count <= 1:
            raise PermissionError(
                "No puedes abandonar el workspace siendo el único OWNER. "
                "Debes asignar otro OWNER antes de salir."
            )

    # 4. Ejecutar abandono (Eliminar registro)
    membership.delete()

    # 5. Notificación (Desacoplada, falla silenciosa si no existe)
    try:
        from apps.notifications.services import notify_user_left_workspace_to_admins
        notify_user_left_workspace_to_admins(
            user_left=user,
            workspace=workspace,
            workspace_id=workspace.id
        )
    except Exception:
        pass

    return {
        'success': True,
        'message': f'Has abandonado el workspace "{workspace.name}" correctamente.',
        'action_performed': True,
        'workspace_name': workspace.name
    }

@transaction.atomic
def service_revert_admin_to_member(
    requester: User, 
    workspace_id: int, 
    target_user_id: int
) -> Dict[str, Any]:
    """
    Revierte el rol de un usuario de ADMIN a MEMBER.
    
    Reglas de Negocio (Invariantes):
    1. Solo el OWNER puede ejecutar esta acción.
    2. El objetivo debe ser miembro activo.
    3. No se puede revertir al OWNER principal.
    4. Idempotencia: Si ya es MEMBER, retorna éxito sin modificar DB.
    
    Efectos Secundarios:
    - Envía notificación al usuario afectado (falla silenciosa si el servicio de notificaciones cae).
    """
    # 1. Obtener Entidades (Fail Fast)
    try:
        workspace = Workspace.objects.get(id=workspace_id)
    except Workspace.DoesNotExist:
        raise ValueError("Workspace no encontrado")

    try:
        target_user = User.objects.get(id=target_user_id)
    except User.DoesNotExist:
        raise ValueError("Usuario no encontrado")

    # 2. Validar Permiso del Solicitante (Solo OWNER)
    try:
        requester_membership = WorkspaceMember.objects.select_related('workspace').get(
            workspace=workspace, 
            user=requester
        )
    except WorkspaceMember.DoesNotExist:
        raise PermissionError("No eres miembro de este workspace")

    if requester_membership.role != WorkspaceMember.Role.OWNER:
        raise PermissionError("Solo el OWNER del workspace puede revertir administradores")

    # 3. Validar Membresía del Objetivo
    try:
        target_membership = WorkspaceMember.objects.get(
            workspace=workspace, 
            user=target_user
        )
    except WorkspaceMember.DoesNotExist:
        raise ValueError("El usuario no es miembro de este workspace")

    # 4. Validaciones de Reglas de Negocio
    if target_membership.role == WorkspaceMember.Role.OWNER:
        raise ValueError("No puedes revertir el rol del OWNER principal")

    # 5. Manejo de Idempotencia
    if target_membership.role != WorkspaceMember.Role.ADMIN:
        return {
            'success': True,
            'message': 'El usuario ya tiene un rol diferente a ADMIN.',
            'action_performed': False,
            'current_role': target_membership.role
        }

    # 6. Ejecutar Cambio de Estado (Transaccional)
    old_role = target_membership.role
    target_membership.role = WorkspaceMember.Role.MEMBER
    target_membership.save(update_fields=['role', 'updated_at'])

    # 7. Efecto Secundario: Notificación (Resiliente)
    # Se intenta notificar, pero si falla, NO se hace rollback del cambio de rol.
    _send_reversion_notification(target_user, workspace.name, requester.username or requester.email)

    return {
        'success': True,
        'message': f'Usuario {target_user.email} revertido exitosamente a MEMBER',
        'action_performed': True,
        'user_email': target_user.email,
        'workspace_name': workspace.name,
        'old_role': old_role,
        'new_role': target_membership.role
    }

def _send_reversion_notification(user: User, workspace_name: str, reverted_by: str) -> None:
    """
    Dispara la notificación de forma desacoplada.
    Si el módulo de notificaciones no existe o falla, se registra el error y se continúa.
    """
    try:
        from apps.notifications.services import notify_user_reverted_to_member
        notify_user_reverted_to_member(
            user=user,
            workspace_name=workspace_name,
            reverted_by=reverted_by,
        )
    except ImportError:
        # Módulo de notificaciones aún no implementado o movido
        pass
    except Exception as e:
        # Loguear error pero no romper la transacción principal
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error al enviar notificación de reversión: {e}")