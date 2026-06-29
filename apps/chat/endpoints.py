# apps/chat/endpoints.py

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from uuid import UUID
from django.core.exceptions import ValidationError
from apps.common.exceptions import PermissionDeniedError

from .models import Workspace, Channel, Message
from .serializers import (
    WorkspaceSerializer,
    WorkspaceDetailSerializer,
    WorkspaceMemberSerializer,
    ChannelSerializer,
    ChannelDetailSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    MessageUpdateSerializer,
    MessageAttachmentSerializer,
)
from .services import (
    create_workspace,
    update_workspace,
    delete_workspace,
    add_member_to_workspace,
    remove_member_from_workspace,
    update_member_role,
    create_channel,
    update_channel,
    delete_channel,
    send_message,
    edit_message,
    delete_message,
    add_attachment_to_message,
    remove_attachment,
    join_workspace,
)
from .selectors import (
    get_user_workspaces,
    get_workspace_by_id,
    get_workspace_channels,
    get_channel_messages,
    get_workspace_members,
    is_workspace_member,
    get_workspace_member,
    search_workspaces,
    invalidate_workspace_cache,
    invalidate_user_workspaces_cache, 
)

import logging
logger = logging.getLogger(__name__)


# ============================================================
# WORKSPACE ENDPOINTS
# ============================================================

class WorkspaceListCreateView(APIView):
    """Listar y crear workspaces"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workspaces = get_user_workspaces(user=request.user)
        serializer = WorkspaceSerializer(workspaces, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        serializer = WorkspaceSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        workspace = create_workspace(
            name=serializer.validated_data['name'],
            slug=serializer.validated_data.get('slug'),
            owner=request.user,
            description=serializer.validated_data.get('description', ''),
        )

        return Response(
            WorkspaceSerializer(workspace, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class WorkspaceDetailView(APIView):
    """Ver, actualizar y eliminar un workspace"""
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id: UUID):
        workspace = get_workspace_by_id(workspace_id=workspace_id)
        
        if not is_workspace_member(workspace_id=workspace.id, user=request.user):
            raise PermissionDeniedError("No eres miembro de este workspace")
        
        serializer = WorkspaceDetailSerializer(workspace, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, workspace_id: UUID):
        workspace = update_workspace(
            workspace_id=workspace_id,
            user=request.user,
            name=request.data.get('name'),
            description=request.data.get('description'),
        )
        
        serializer = WorkspaceSerializer(workspace, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, workspace_id: UUID):
        delete_workspace(workspace_id=workspace_id, user=request.user)
        return Response(
            {"message": "Workspace eliminado exitosamente"},
            status=status.HTTP_204_NO_CONTENT
        )


class WorkspaceMembersView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, workspace_id):
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            
            is_member = WorkspaceMember.objects.filter(
                workspace=workspace,
                user=request.user
            ).exists()
            
            if not is_member:
                return Response(
                    {'error': 'No eres miembro de este workspace'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            memberships = workspace.memberships.select_related('user').all()
            
            members_data = []
            for membership in memberships:
                user = membership.user
                members_data.append({
                    'id': str(membership.id),
                    'user_id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'role': membership.role,
                    'user': {
                        'id': str(user.id),
                        'username': user.username,
                        'email': user.email,
                        'avatar': user.avatar.url if user.avatar else None
                    }
                })
            
            return Response({
                'members': members_data,
                'count': len(members_data)
            })
            
        except Workspace.DoesNotExist:
            return Response(
                {'error': 'Workspace no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"❌ Error en WorkspaceMembersView: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, workspace_id):
        """Eliminar un miembro del workspace (expulsar o abandonar)"""
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            
            # Verificar que el usuario que hace la petición sea miembro
            user_membership = WorkspaceMember.objects.filter(
                workspace=workspace,
                user=request.user
            ).first()
            
            if not user_membership:
                return Response(
                    {'error': 'No eres miembro de este workspace'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            #  Obtener el usuario a eliminar
            user_id = request.data.get('user_id')
            if not user_id:
                return Response(
                    {'error': 'user_id es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            target_membership = WorkspaceMember.objects.filter(
                workspace=workspace,
                user_id=user_id
            ).first()
            
            if not target_membership:
                return Response(
                    {'error': 'El usuario no es miembro de este workspace'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            #  Si el usuario se está eliminando a sí mismo (ABANDONAR)
            if str(target_membership.user_id) == str(request.user.id):
                #  PERMITIR: cualquier usuario puede abandonar el workspace
                # Solo verificar que no sea el owner (el owner no puede abandonar, debe eliminar el workspace)
                if target_membership.role == 'owner':
                    return Response(
                        {'error': 'Eres el owner del workspace. No puedes abandonarlo, debes eliminarlo.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                #  Eliminar la membresía (abandonar)
                target_membership.delete()
                
                # Invalidar cache
                invalidate_workspace_cache(workspace_id=workspace.id)
                invalidate_user_workspaces_cache(user_id=request.user.id)
                
                return Response({
                    'success': True,
                    'message': f'Has abandonado el workspace {workspace.name}'
                }, status=status.HTTP_200_OK)
            
            # Si es otro usuario (EXPULSAR) - requere permisos de admin/owner
            if user_membership.role not in ['owner', 'admin']:
                return Response(
                    {'error': 'Solo el owner o admin pueden expulsar miembros'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # ❌ No se puede expulsar al owner
            if target_membership.role == 'owner':
                return Response(
                    {'error': 'No se puede expulsar al owner del workspace'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            #  Eliminar la membresía (expulsar)
            target_membership.delete()
            
            #  Invalidar cache
            invalidate_workspace_cache(workspace_id=workspace.id)
            invalidate_user_workspaces_cache(user_id=request.user.id)
            invalidate_user_workspaces_cache(user_id=target_membership.user_id)
            
            return Response({
                'success': True,
                'message': f'Usuario expulsado del workspace {workspace.name}'
            }, status=status.HTTP_200_OK)
            
        except Workspace.DoesNotExist:
            return Response(
                {'error': 'Workspace no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"❌ Error en DELETE WorkspaceMembersView: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WorkspaceMemberRoleView(APIView):
    """Actualizar rol de un miembro"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, workspace_id: UUID, user_id: UUID):
        role = request.data.get('role')
        
        if not role:
            return Response(
                {"error": "role es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if role not in ['owner', 'admin', 'member']:
            return Response(
                {"error": "role inválido. Debe ser: owner, admin o member"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.accounts.selectors import get_user_by_id
        try:
            user_to_update = get_user_by_id(user_id=user_id)
        except:
            return Response(
                {"error": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        membership = update_member_role(
            workspace_id=workspace_id,
            user_to_update=user_to_update,
            updated_by=request.user,
            role=role,
        )
        
        serializer = WorkspaceMemberSerializer(membership)
        return Response(serializer.data)


class WorkspaceSearchView(APIView):
    """Buscar workspaces públicos"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        logger.info(f"[Search Workspaces] Query: {query}")

        if not query or len(query) < 2:
            return Response({
                'workspaces': [],
                'message': 'Ingresa al menos 2 caracteres para buscar'
            })

        workspaces = search_workspaces(
            query=query,
            user=request.user,
            limit=20,
        )

        from .serializers import WorkspaceSerializer
        serializer = WorkspaceSerializer(workspaces, many=True, context={'request': request})
        
        return Response({
            'workspaces': serializer.data,
            'total': len(workspaces),
            'query': query,
        })


class WorkspaceJoinView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, workspace_id):
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            
            existing_membership = WorkspaceMember.objects.filter(
                workspace=workspace,
                user=request.user
            ).first()
            
            if existing_membership:
                return Response({
                    'success': True,
                    'already_member': True,
                    'message': 'Ya eres miembro de este workspace',
                    'workspace_id': str(workspace_id),
                    'role': existing_membership.role
                }, status=status.HTTP_200_OK)
            
            WorkspaceMember.objects.create(
                workspace=workspace,
                user=request.user,
                role=WorkspaceMember.Role.MEMBER
            )
            
            #  Invalidar ambos caches
            invalidate_workspace_cache(workspace_id=workspace_id)
            invalidate_user_workspaces_cache(user_id=request.user.id)  
            
            return Response({
                'success': True,
                'message': f'Te has unido a {workspace.name}',
                'workspace_id': str(workspace_id),
                'workspace': {
                    'id': str(workspace.id),
                    'name': workspace.name,
                    'slug': workspace.slug,
                    'description': workspace.description
                }
            }, status=status.HTTP_201_CREATED)
            
        except Workspace.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Workspace no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


from apps.chat.models import Workspace, WorkspaceMember

class CheckWorkspaceMembershipView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, workspace_id):
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            is_member = workspace.memberships.filter(user=request.user).exists()
            
            return Response({
                'is_member': is_member,
                'workspace_id': str(workspace_id),
                'user_id': str(request.user.id)
            })
            
        except Workspace.DoesNotExist:
            return Response(
                {'is_member': False, 'error': 'Workspace no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Error en CheckWorkspaceMembershipView: {e}")
            return Response(
                {'is_member': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# CHANNEL ENDPOINTS
# ============================================================

# apps/chat/endpoints.py

class ChannelListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, workspace_id):
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            
            is_member = WorkspaceMember.objects.filter(
                workspace=workspace,
                user=request.user
            ).exists()
            
            if not is_member:
                return Response(
                    {'error': 'No eres miembro de este workspace'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            channels = workspace.channels.all().order_by('name')
            serializer = ChannelSerializer(channels, many=True)
            return Response(serializer.data)
            
        except Workspace.DoesNotExist:
            return Response(
                {'error': 'Workspace no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"❌ Error en ChannelListCreateView: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, workspace_id):
        """Crear un nuevo canal en el workspace"""
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            
            # Verificar que el usuario sea miembro
            is_member = WorkspaceMember.objects.filter(
                workspace=workspace,
                user=request.user
            ).exists()
            
            if not is_member:
                return Response(
                    {'error': 'No eres miembro de este workspace'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Verificar que el usuario tenga permisos para crear canales
            
            membership = WorkspaceMember.objects.filter(
                workspace=workspace,
                user=request.user
            ).first()
            
            if membership and membership.role not in ['owner', 'admin']:
                return Response(
                    {'error': 'No tienes permisos para crear canales'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            #  Validar datos
            name = request.data.get('name')
            if not name or not name.strip():
                return Response(
                    {'error': 'El nombre del canal es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            #  Crear canal usando el servicio
            from .services import create_channel
            channel = create_channel(
                workspace_id=workspace.id,
                name=name.strip(),
                created_by=request.user,
                description=request.data.get('description', ''),
                channel_type=request.data.get('channel_type', 'text'),
            )
            
            serializer = ChannelSerializer(channel)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Workspace.DoesNotExist:
            return Response(
                {'error': 'Workspace no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f"❌ Error en ChannelListCreateView POST: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ChannelDetailView(APIView):
    """Ver, actualizar y eliminar un canal"""
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id: UUID, channel_id: UUID):
        workspace = get_workspace_by_id(workspace_id=workspace_id)
        
        if not is_workspace_member(workspace_id=workspace.id, user=request.user):
            raise PermissionDeniedError("No eres miembro de este workspace")
        
        channel = get_object_or_404(Channel, id=channel_id, workspace_id=workspace_id)
        serializer = ChannelDetailSerializer(channel, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, workspace_id: UUID, channel_id: UUID):
        channel = update_channel(
            channel_id=channel_id,
            user=request.user,
            name=request.data.get('name'),
            description=request.data.get('description'),
        )
        
        serializer = ChannelSerializer(channel, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, workspace_id: UUID, channel_id: UUID):
        delete_channel(channel_id=channel_id, user=request.user)
        return Response(
            {"message": "Canal eliminado exitosamente"},
            status=status.HTTP_204_NO_CONTENT
        )


# ============================================================
# MESSAGE ENDPOINTS
# ============================================================

# apps/chat/endpoints.py - MessageListCreateView

class MessageListCreateView(APIView):
    """Listar y enviar mensajes en un canal"""
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id: UUID, channel_id: UUID):
        workspace = get_workspace_by_id(workspace_id=workspace_id)
        
        if not is_workspace_member(workspace_id=workspace.id, user=request.user):
            raise PermissionDeniedError("No eres miembro de este workspace")
        
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        
        result = get_channel_messages(
            channel_id=channel_id,
            limit=limit,
            offset=offset,
        )
        
        serializer = MessageSerializer(result['messages'], many=True, context={'request': request})
        return Response({
            'messages': serializer.data,
            'total': result['total'],
            'limit': result['limit'],
            'offset': result['offset'],
        })

    def post(self, request, workspace_id: UUID, channel_id: UUID):
        logger.info(f"[POST Message] Datos recibidos: {request.data}")
        logger.info(f"[POST Message] Archivos: {request.FILES}")
        
        workspace = get_workspace_by_id(workspace_id=workspace_id)
        
        if not is_workspace_member(workspace_id=workspace.id, user=request.user):
            raise PermissionDeniedError("No eres miembro de este workspace")
        
        # OBTENER CONTENT Y FILE
        content = request.data.get('content', '')
        file = request.FILES.get('file')
        
        # Validar: si no hay contenido y no hay archivo, error
        if not content and not file:
            return Response(
                {"error": "Debes proporcionar un mensaje o un archivo"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        #  Si solo hay archivo, content será ''
        # Si hay texto, usarlo
        final_content = content if content else ''
        
        #  Crear el mensaje
        message = send_message(
            channel_id=channel_id,
            author=request.user,
            content=final_content,
        )
        
        # Si hay archivo, adjuntarlo
        if file:
            try:
                attachment = add_attachment_to_message(
                    message_id=message.id,
                    user=request.user,
                    file=file,
                    original_name=file.name,
                    mime_type=file.content_type or 'application/octet-stream',
                    size=file.size,
                )
                logger.info(f"[POST Message] Archivo adjunto: {attachment.id}")
            except Exception as e:
                logger.error(f"[POST Message] Error al adjuntar archivo: {e}")
                # No fallar el mensaje si el archivo falla
                # Pero loguearlo
        
        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

class MessageDetailView(APIView):
    """Ver, editar y eliminar un mensaje"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, workspace_id: UUID, channel_id: UUID, message_id: UUID):
        serializer = MessageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        message = edit_message(
            message_id=message_id,
            user=request.user,
            new_content=serializer.validated_data['content'],
        )
        
        return Response(
            MessageSerializer(message, context={'request': request}).data
        )

    def delete(self, request, workspace_id: UUID, channel_id: UUID, message_id: UUID):
        delete_message(message_id=message_id, user=request.user)
        return Response(
            {"message": "Mensaje eliminado exitosamente"},
            status=status.HTTP_204_NO_CONTENT
        )


# ============================================================
# ATTACHMENT ENDPOINTS
# ============================================================

class AttachmentUploadView(APIView):
    """Subir un archivo adjunto a un mensaje"""
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id: UUID, channel_id: UUID, message_id: UUID):
        workspace = get_workspace_by_id(workspace_id=workspace_id)
        
        if not is_workspace_member(workspace_id=workspace.id, user=request.user):
            raise PermissionDeniedError("No eres miembro de este workspace")
        
        file = request.FILES.get('file')
        if not file:
            return Response(
                {"error": "file es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        MAX_FILE_SIZE = 10 * 1024 * 1024
        if file.size > MAX_FILE_SIZE:
            return Response(
                {"error": f"El archivo no puede superar los 10MB"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        attachment = add_attachment_to_message(
            message_id=message_id,
            user=request.user,
            file=file,
            original_name=file.name,
            mime_type=file.content_type or 'application/octet-stream',
            size=file.size,
        )
        
        serializer = MessageAttachmentSerializer(attachment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AttachmentDeleteView(APIView):
    """Eliminar un archivo adjunto"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, workspace_id: UUID, channel_id: UUID, message_id: UUID, attachment_id: UUID):
        remove_attachment(
            attachment_id=attachment_id,
            user=request.user,
        )
        
        return Response(
            {"message": "Adjunto eliminado exitosamente"},
            status=status.HTTP_204_NO_CONTENT
        )