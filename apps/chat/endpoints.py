# apps/chat/endpoints.py

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from uuid import UUID
from django.core.exceptions import ValidationError
from apps.common.exceptions import PermissionDeniedError

from .models import Workspace, Channel, Message, WorkspaceMember
from apps.chat.serializers import (
    WorkspaceSerializer,
    WorkspaceDetailSerializer,
    WorkspaceMemberSerializer,
    ChannelSerializer,
    ChannelDetailSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    MessageUpdateSerializer,
    MessageAttachmentSerializer,
    InviteMemberSerializer,
    WorkspaceMemberResponseSerializer,
    LeaveWorkspaceResponseSerializer,
    RevertAdminResponseSerializer,
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
    invite_member_to_workspace,
    service_leave_workspace,
    service_revert_admin_to_member
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
    get_user_by_email_from_invite
)


from apps.notifications.services import (
    notify_user_expelled_from_workspace,
    notify_user_role_changed,
    notify_user_joined_workspace,
    notify_user_left_workspace,
    notify_user_workspace_deleted,
    notify_user_channel_created,
    notify_user_channel_deleted,
    notify_user_promoted_to_admin,
    notify_user_reverted_to_member,
)

from django.contrib.auth import get_user_model
User = get_user_model()  
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

        # ELIMINAR 'slug' DE LA LLAMADA (se genera automáticamente)
        workspace = create_workspace(
            name=serializer.validated_data['name'],
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
                user=request.user,
                status=WorkspaceMember.Status.ACTIVE
            ).exists()
            
            if not is_member:
                return Response(
                    {'error': 'No eres miembro de este workspace'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            memberships = workspace.memberships.select_related('user').filter(
                status=WorkspaceMember.Status.ACTIVE
            )
            
            members_data = []
            for membership in memberships:
                user = membership.user
                members_data.append({
                    'id': str(membership.id),
                    'user_id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'role': membership.role,
                    'status': membership.status,
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
            
            # Verificar que el usuario que hace la petición sea miembro ACTIVO
            user_membership = WorkspaceMember.objects.filter(
                workspace=workspace,
                user=request.user,
                status=WorkspaceMember.Status.ACTIVE
            ).first()
            
            if not user_membership:
                return Response(
                    {'error': 'No eres miembro de este workspace'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Obtener el usuario a eliminar
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
            
            # Si el usuario se está eliminando a sí mismo (ABANDONAR)
            if str(target_membership.user_id) == str(request.user.id):
                # PERMITIR: cualquier usuario puede abandonar el workspace
                # Solo verificar que no sea el owner (el owner no puede abandonar, debe eliminar el workspace)
                if target_membership.role == 'owner':
                    return Response(
                        {'error': 'Eres el owner del workspace. No puedes abandonarlo, debes eliminarlo.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # GUARDAR DATOS DEL USUARIO QUE ABANDONA
                user_left = target_membership.user
                workspace_name = workspace.name
                workspace_id_str = str(workspace.id)
                
                # Eliminar la membresía (abandonar)
                target_membership.delete()
                
                # Invalidar cache
                invalidate_workspace_cache(workspace_id=workspace.id)
                invalidate_user_workspaces_cache(user_id=request.user.id)
                
                # ENVIAR NOTIFICACIÓN A OWNERS Y ADMINS
                try:
                    from apps.notifications.services import notify_user_left_workspace_to_admins
                    notify_user_left_workspace_to_admins(
                        user_left=user_left,
                        workspace=workspace,
                        workspace_id=workspace.id,
                    )
                    logger.info(f"✅ Notificación de abandono enviada a Owners y Admins")
                except Exception as e:
                    logger.error(f"❌ Error al enviar notificación de abandono: {e}")
                
                return Response({
                    'success': True,
                    'message': f'Has abandonado el workspace {workspace.name}'
                }, status=status.HTTP_200_OK)
            
            # Si es otro usuario (EXPULSAR) - requiere permisos de admin/owner
            if user_membership.role not in ['owner', 'admin']:
                return Response(
                    {'error': 'Solo el owner o admin pueden expulsar miembros'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # No se puede expulsar al owner
            if target_membership.role == 'owner':
                return Response(
                    {'error': 'No se puede expulsar al owner del workspace'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Eliminar la membresía (expulsar)
            target_membership.delete()
            
            # Invalidar cache
            invalidate_workspace_cache(workspace_id=workspace.id)
            invalidate_user_workspaces_cache(user_id=request.user.id)
            invalidate_user_workspaces_cache(user_id=target_membership.user_id)
            
            # Enviar notificación de expulsión al usuario expulsado
            try:
                from apps.notifications.services import notify_user_expelled_from_workspace
                notify_user_expelled_from_workspace(
                    user=target_membership.user,
                    workspace_name=workspace.name,
                    workspace_id=workspace.id,
                    expelled_by=request.user.username or request.user.email,
                )
            except Exception as e:
                logger.error(f"Error al enviar notificación de expulsión: {e}")
            
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
            print(f"Error en DELETE WorkspaceMembersView: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LeaveWorkspaceView(APIView):
    """
    Endpoint para que un usuario abandone voluntariamente un workspace.
    URL: POST /api/workspaces/<id>/leave/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id):
        try:
            result = service_leave_workspace(
                user=request.user,
                workspace_id=workspace_id
            )
            
            return Response(
                LeaveWorkspaceResponseSerializer(result).data,
                status=status.HTTP_200_OK
            )

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
            
        except PermissionError as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
            
        except Exception as e:
            logger.error(f"Error al abandonar workspace: {e}")
            return Response(
                {'error': 'Error interno al procesar la solicitud'},
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


class CheckWorkspaceMembershipView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, workspace_id):
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            
            try:
                membership = WorkspaceMember.objects.get(
                    workspace=workspace,
                    user=request.user
                )
                
                
                return Response({
                    'is_member': True,
                    'workspace_id': str(workspace_id),
                    'user_id': str(request.user.id),
                    'role': membership.role,  
                    'email': request.user.email,
                })
                
            except WorkspaceMember.DoesNotExist:
                return Response({
                    'is_member': False,
                    'workspace_id': str(workspace_id),
                    'user_id': str(request.user.id),
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

class PromoverAdmin(APIView):
    """
    Endpoint para ascender a un miembro a ADMIN.
    Solo el OWNER del workspace puede hacer esto.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, workspace_id):
        # ============================================================
        # 1. LOG DE INICIO DE PETICIÓN
        # ============================================================
        logger.info("=" * 60)
        logger.info(f"🚀 [PROMOTE-ADMIN] Iniciando promoción")
        logger.info(f"📋 [PROMOTE-ADMIN] Usuario solicitante: {request.user.email} (ID: {request.user.id})")
        logger.info(f"📋 [PROMOTE-ADMIN] Workspace ID: {workspace_id}")
        logger.info(f"📋 [PROMOTE-ADMIN] Request data: {request.data}")
        logger.info("=" * 60)
        
        # ============================================================
        # 2. VALIDAR user_id EN EL BODY
        # ============================================================
        user_id = request.data.get('user_id')
        
        if not user_id:
            logger.warning(f"⚠️ [PROMOTE-ADMIN] user_id no proporcionado en el body")
            return Response(
                {'error': 'user_id es requerido en el body de la petición'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"✅ [PROMOTE-ADMIN] user_id recibido: {user_id}")
        
        try:
            # ============================================================
            # 3. OBTENER WORKSPACE Y USUARIO
            # ============================================================
            logger.info("🔍 [PROMOTE-ADMIN] Buscando workspace y usuario...")
            
            workspace = Workspace.objects.get(id=workspace_id)
            logger.info(f"✅ [PROMOTE-ADMIN] Workspace encontrado: {workspace.name} (ID: {workspace.id})")
            
            user = User.objects.get(id=user_id)
            logger.info(f"✅ [PROMOTE-ADMIN] Usuario objetivo encontrado: {user.email} (ID: {user.id})")
            
            # ============================================================
            # 4. VERIFICAR QUE EL SOLICITANTE ES MIEMBRO DEL WORKSPACE
            # ============================================================
            logger.info("🔍 [PROMOTE-ADMIN] Verificando membresía del solicitante...")
            
            try:
                requester_membership = WorkspaceMember.objects.get(
                    workspace=workspace,
                    user=request.user
                )
                logger.info(f"✅ [PROMOTE-ADMIN] Solicitante es miembro. Rol: {requester_membership.role}")
            except WorkspaceMember.DoesNotExist:
                logger.warning(f"⚠️ [PROMOTE-ADMIN] Solicitante NO es miembro del workspace")
                return Response(
                    {'error': 'No eres miembro de este workspace'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # ============================================================
            # 5. VERIFICAR QUE EL SOLICITANTE ES OWNER
            # ============================================================
            logger.info("🔍 [PROMOTE-ADMIN] Verificando que el solicitante es OWNER...")
            
            if requester_membership.role != WorkspaceMember.Role.OWNER:
                logger.warning(f"⚠️ [PROMOTE-ADMIN] Solicitante NO es OWNER. Rol actual: {requester_membership.role}")
                return Response(
                    {'error': 'Solo el owner del workspace puede ascender a admin'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            logger.info(f"✅ [PROMOTE-ADMIN] Solicitante es OWNER. Continuando...")
            
            # ============================================================
            # 6. VERIFICAR QUE EL USUARIO OBJETIVO ES MIEMBRO
            # ============================================================
            logger.info("🔍 [PROMOTE-ADMIN] Verificando que el usuario objetivo es miembro...")
            
            is_member = WorkspaceMember.objects.filter(
                workspace=workspace,
                user=user
            ).exists()
            
            if not is_member:
                logger.warning(f"⚠️ [PROMOTE-ADMIN] Usuario objetivo NO es miembro del workspace")
                return Response(
                    {'error': 'El usuario no es miembro del workspace'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"✅ [PROMOTE-ADMIN] Usuario objetivo es miembro")
            
            # ============================================================
            # 7. OBTENER EL MIEMBRO Y VERIFICAR ROL ACTUAL
            # ============================================================
            logger.info("🔍 [PROMOTE-ADMIN] Obteniendo membresía del usuario objetivo...")
            
            member = WorkspaceMember.objects.get(workspace=workspace, user=user)
            logger.info(f"📋 [PROMOTE-ADMIN] Rol actual del usuario objetivo: {member.role}")
            
            # ============================================================
            # 8. VERIFICAR QUE NO SEA OWNER
            # ============================================================
            if member.role == WorkspaceMember.Role.OWNER:
                logger.warning(f"⚠️ [PROMOTE-ADMIN] El usuario objetivo es OWNER. No se puede cambiar su rol.")
                return Response(
                    {'error': 'No puedes cambiar el rol del owner'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # ============================================================
            # 9. VERIFICAR QUE YA NO SEA ADMIN
            # ============================================================
            if member.role == WorkspaceMember.Role.ADMIN:
                logger.info(f"ℹ️ [PROMOTE-ADMIN] El usuario objetivo YA es ADMIN. No se requiere acción.")
                return Response({
                    'success': True,
                    'message': 'Este usuario ya es admin',
                    'user_id': str(user_id),
                    'workspace_id': str(workspace_id)
                }, status=status.HTTP_200_OK)
            
            # ============================================================
            # 10. PROMOVER A ADMIN
            # ============================================================
            logger.info(f"🔄 [PROMOTE-ADMIN] Promoviendo a {user.email} de '{member.role}' a 'admin'...")
            
            member.role = WorkspaceMember.Role.ADMIN
            member.save()
            
            logger.info(f"✅ [PROMOTE-ADMIN] Usuario {user.email} promovido a ADMIN exitosamente")
            
            # ============================================================
            # 11. ENVIAR NOTIFICACIÓN
            # ============================================================
            try:
                logger.info("📧 [PROMOTE-ADMIN] Enviando notificación al usuario ascendido...")
                from apps.notifications.services import notify_user_promoted_to_admin
                notify_user_promoted_to_admin(
                    user=user,
                    workspace_name=workspace.name,
                    promoted_by=request.user.username
                )
                logger.info(f"✅ [PROMOTE-ADMIN] Notificación enviada a {user.email}")
            except Exception as e:
                logger.error(f"❌ [PROMOTE-ADMIN] Error al enviar notificación: {str(e)}")
                # No fallar la promoción por error de notificación
            
            # ============================================================
            # 12. RESPUESTA EXITOSA
            # ============================================================
            logger.info("=" * 60)
            logger.info(f"🎉 [PROMOTE-ADMIN] ¡PROMOCIÓN EXITOSA!")
            logger.info(f"📋 [PROMOTE-ADMIN] Usuario: {user.email} → ADMIN")
            logger.info(f"📋 [PROMOTE-ADMIN] Workspace: {workspace.name}")
            logger.info(f"📋 [PROMOTE-ADMIN] Promovido por: {request.user.email}")
            logger.info("=" * 60)
            
            return Response({
                'success': True,
                'message': f'Usuario {user.email} promovido a admin',
                'user_id': str(user_id),
                'user_email': user.email,
                'workspace_id': str(workspace_id),
                'workspace_name': workspace.name,
                'role': member.role
            }, status=status.HTTP_200_OK)
            
        except Workspace.DoesNotExist:
            logger.error(f"❌ [PROMOTE-ADMIN] Workspace no encontrado: {workspace_id}")
            return Response(
                {'error': 'Workspace no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        except User.DoesNotExist:
            logger.error(f"❌ [PROMOTE-ADMIN] Usuario no encontrado: {user_id}")
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            logger.error(f"💥 [PROMOTE-ADMIN] Error inesperado: {str(e)}")
            logger.error(f"📋 [PROMOTE-ADMIN] Traceback:", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RevertirAdmin(APIView):
    """
    Endpoint para revertir un ADMIN a MEMBER.
    Solo el OWNER del workspace puede hacer esto.
    URL: POST /api/workspaces/<id>/revert-admin/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id):
        # ============================================================
        # FASE 1: LOG DE INICIO DE PETICIÓN (TRAZABILIDAD)
        # ============================================================
        logger.info("=" * 60)
        logger.info(f"🔄 [REVERTIR-ADMIN] Iniciando reversión de admin")
        logger.info(f"📋 [REVERTIR-ADMIN] Usuario solicitante: {request.user.email} (ID: {request.user.id})")
        logger.info(f"📋 [REVERTIR-ADMIN] Workspace ID: {workspace_id}")
        logger.info("=" * 60)

        # ============================================================
        # FASE 2: VALIDACIÓN TEMPRANA DE INPUTS
        # ============================================================
        user_id = request.data.get('user_id')

        if not user_id:
            logger.warning(f"⚠️ [REVERTIR-ADMIN] user_id no proporcionado en el body")
            return Response(
                {'error': 'user_id es requerido en el body de la petición'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"✅ [REVERTIR-ADMIN] user_id recibido: {user_id}")

        try:
            # ============================================================
            # FASE 3: EJECUCIÓN DEL SERVICIO (LÓGICA DE NEGOCIO)
            # ============================================================
            # El servicio se encarga de:
            # 1. Obtener Workspace y Usuario (con logs internos)
            # 2. Validar permisos de OWNER
            # 3. Validar reglas de negocio (no revertir owner, idempotencia)
            # 4. Ejecutar cambio de rol (transaccional)
            # 5. Disparar notificación (efecto secundario resiliente)
            
            logger.info(f"⚙️ [REVERTIR-ADMIN] Delegando ejecución al servicio...")
            
            result = service_revert_admin_to_member(
                requester=request.user,
                workspace_id=workspace_id,
                target_user_id=user_id
            )

            # ============================================================
            # FASE 4: CONSTRUCCIÓN DE RESPUESTA EXITOSA
            # ============================================================
            logger.info(f"✅ [REVERTIR-ADMIN] Servicio ejecutado correctamente. Acción realizada: {result.get('action_performed')}")
            
            # Usamos el serializer para garantizar la estructura de la respuesta
            serializer = RevertAdminResponseSerializer(result)
            
            logger.info("=" * 60)
            if result.get('action_performed'):
                logger.info(f"🎉 [REVERTIR-ADMIN] ¡REVERSIÓN EXITOSA!")
                logger.info(f"📋 [REVERTIR-ADMIN] Usuario: {result.get('user_email')} → MEMBER")
                logger.info(f"📋 [REVERTIR-ADMIN] Workspace: {result.get('workspace_name')}")
            else:
                logger.info(f"ℹ️ [REVERTIR-ADMIN] Operación idempotente (sin cambios necesarios)")
            logger.info("=" * 60)

            return Response(serializer.data, status=status.HTTP_200_OK)

        # ============================================================
        # FASE 5: MANEJO ESPECÍFICO DE ERRORES (TRAZABILIDAD DE FALLOS)
        # ============================================================
        
        except ValueError as e:
            # Errores de entidad no encontrada o validación de negocio simple
            error_msg = str(e)
            logger.error(f"❌ [REVERTIR-ADMIN] Error de validación/entidad: {error_msg}")
            
            # Determinamos el código HTTP según el contexto del error
            if "no encontrado" in error_msg.lower():
                return Response({'error': error_msg}, status=status.HTTP_404_NOT_FOUND)
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)

        except PermissionError as e:
            # Errores de permisos (No es miembro, no es OWNER)
            error_msg = str(e)
            logger.warning(f"⚠️ [REVERTIR-ADMIN] Denegado por permisos: {error_msg}")
            return Response({'error': error_msg}, status=status.HTTP_403_FORBIDDEN)

        except Exception as e:
            # Errores inesperados (Crash del sistema, DB down, etc.)
            logger.error(f"💥 [REVERTIR-ADMIN] Error inesperado/crítico: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Error interno del servidor al procesar la solicitud'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class WorkspaceInviteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id: UUID):
        logger.info("=" * 60)
        logger.info("INICIO [WorkspaceInviteView] - Invitando miembro")
        logger.info(f"Workspace ID: {workspace_id}")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info("=" * 60)

        try:
            
            serializer = InviteMemberSerializer(
                data=request.data,
                context={
                    'workspace_id': workspace_id,
                    'user': request.user  
                }
            )
            serializer.is_valid(raise_exception=True)

            member = invite_member_to_workspace(
                workspace_id=workspace_id,
                invited_by=request.user,
                email=serializer.validated_data['email'],
                role=serializer.validated_data.get('role', WorkspaceMember.Role.MEMBER),
            )

            response_serializer = WorkspaceMemberResponseSerializer(member)

            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [WorkspaceInviteView] - Usuario invitado: {member.user.email}")
            logger.info("=" * 60)

            return Response({
                'success': True,
                'message': f'Usuario {member.user.email} invitado exitosamente',
                'member': response_serializer.data
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            logger.warning(f"WARNING [WorkspaceInviteView] - Error de validación: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except PermissionDeniedError as e:
            logger.warning(f"WARNING [WorkspaceInviteView] - Error de permisos: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
            
        except Exception as e:
            logger.error(f"ERROR [WorkspaceInviteView] - Error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Error al invitar al usuario'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AcceptInvitationView(APIView):
    """Aceptar una invitación a un workspace"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, membership_id: UUID):
        logger.info("=" * 60)
        logger.info("INICIO [AcceptInvitationView] - Aceptando invitación")
        logger.info(f"Membership ID: {membership_id}")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info("=" * 60)
        
        try:
            logger.info("PROCESO [AcceptInvitationView] - Buscando invitación pendiente")
            
            member = WorkspaceMember.objects.get(
                id=membership_id,
                user=request.user,
                status=WorkspaceMember.Status.PENDING
            )
            
            logger.info(f"PROCESO [AcceptInvitationView] - Invitación encontrada: {member.id}")
            logger.info(f"PROCESO [AcceptInvitationView] - Workspace: {member.workspace.name}")
            logger.info(f"PROCESO [AcceptInvitationView] - Role: {member.role}")
            
            if member.is_expired():
                logger.warning(f"WARNING [AcceptInvitationView] - Invitación expirada")
                member.status = WorkspaceMember.Status.REJECTED
                member.save()
                
                logger.info("=" * 60)
                logger.info("FIN [AcceptInvitationView] - Invitación expirada")
                logger.info("=" * 60)
                
                return Response({
                    'success': False,
                    'error': 'La invitación ha expirado'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info("PROCESO [AcceptInvitationView] - Cambiando status a ACTIVE")
            
            member.status = WorkspaceMember.Status.ACTIVE
            member.save(update_fields=['status', 'updated_at'])
            
            # ELIMINAR LA NOTIFICACIÓN
            try:
                from apps.notifications.models import Notification
                import json
                
                # Buscar notificaciones no leídas que contengan membership_id en el mensaje JSON
                notifications = Notification.objects.filter(
                    user=request.user
                )
                
                for notification in notifications:
                    try:
                        data = json.loads(notification.message)
                        if data.get('membership_id') == str(membership_id):
                            notification.delete()
                            logger.info(f"✅ Notificación eliminada: {notification.id}")
                            break
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        continue
                    
            except Exception as e:
                logger.error(f"❌ Error al eliminar notificación: {e}")
            
            logger.info(f"PROCESO [AcceptInvitationView] - Usuario {request.user.email} unido a {member.workspace.name}")
            
            logger.info("=" * 60)
            logger.info("FIN EXITOSO [AcceptInvitationView] - Usuario aceptó la invitación correctamente")
            logger.info("=" * 60)
            
            return Response({
                'success': True,
                'message': f'Te has unido a {member.workspace.name}',
                'workspace_id': str(member.workspace.id),
                'workspace_name': member.workspace.name,
            })
            
        except WorkspaceMember.DoesNotExist:
            logger.warning(f"WARNING [AcceptInvitationView] - Invitación no encontrada")
            logger.info("=" * 60)
            logger.info("FIN [AcceptInvitationView] - Invitación no encontrada")
            logger.info("=" * 60)
            
            return Response({
                'success': False,
                'error': 'Invitación no encontrada o ya procesada'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except ValueError as e:
            logger.error(f"ERROR [AcceptInvitationView] - Error: {str(e)}")
            logger.info("=" * 60)
            logger.info("FIN [AcceptInvitationView] - Error al aceptar invitación")
            logger.info("=" * 60)
            
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class RejectInvitationView(APIView):
    """Rechazar una invitación a un workspace"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, membership_id: UUID):
        logger.info("=" * 60)
        logger.info("INICIO [RejectInvitationView] - Rechazando invitación")
        logger.info(f"Membership ID: {membership_id}")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info("=" * 60)
        
        try:
            member = WorkspaceMember.objects.get(
                id=membership_id,
                user=request.user,
                status=WorkspaceMember.Status.PENDING
            )
            
            logger.info(f"PROCESO [RejectInvitationView] - Invitación encontrada: {member.id}")
            
            member.reject()
            
            # ELIMINAR LA NOTIFICACIÓN
            try:
                from apps.notifications.models import Notification
                import json
                
                notifications = Notification.objects.filter(
                    user=request.user
                )
                
                for notification in notifications:
                    try:
                        data = json.loads(notification.message)
                        if data.get('membership_id') == str(membership_id):
                            notification.delete()
                            logger.info(f"✅ Notificación eliminada: {notification.id}")
                            break
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        continue
                    
            except Exception as e:
                logger.error(f"❌ Error al eliminar notificación: {e}")
            
            logger.info("=" * 60)
            logger.info("FIN EXITOSO [RejectInvitationView] - Usuario rechazó la invitación correctamente")
            logger.info("=" * 60)
            
            return Response({
                'success': True,
                'message': 'Has rechazado la invitación'
            })
            
        except WorkspaceMember.DoesNotExist:
            logger.warning(f"WARNING [RejectInvitationView] - Invitación no encontrada")
            logger.info("=" * 60)
            logger.info("FIN [RejectInvitationView] - Invitación no encontrada")
            logger.info("=" * 60)
            
            return Response({
                'success': False,
                'error': 'Invitación no encontrada o ya procesada'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except ValueError as e:
            logger.error(f"ERROR [RejectInvitationView] - Error: {str(e)}")
            logger.info("=" * 60)
            logger.info("FIN [RejectInvitationView] - Error al rechazar invitación")
            logger.info("=" * 60)
            
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
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
        """
        Eliminar un mensaje con verificación de permisos.
        
        Permisos:
        - El autor del mensaje siempre puede eliminarlo
        - Owner del workspace puede eliminar cualquier mensaje
        - Admin puede eliminar mensajes de miembros (role='member') pero NO de owners
        - Member solo puede eliminar sus propios mensajes
        """
        try:
            # Obtener el mensaje
            message = get_object_or_404(Message, id=message_id)
            channel = get_object_or_404(Channel, id=channel_id, workspace_id=workspace_id)
            
            # Verificar que el mensaje pertenece al canal
            if message.channel_id != channel.id:
                return Response(
                    {'error': 'El mensaje no pertenece a este canal'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verificar que el usuario es miembro del workspace
            try:
                member = WorkspaceMember.objects.get(
                    workspace_id=workspace_id,
                    user=request.user
                )
            except WorkspaceMember.DoesNotExist:
                return Response(
                    {'error': 'No eres miembro de este workspace'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Obtener el autor del mensaje
            try:
                author_member = WorkspaceMember.objects.get(
                    workspace_id=workspace_id,
                    user=message.author
                )
                author_role = author_member.role
            except WorkspaceMember.DoesNotExist:
                # Si el autor ya no es miembro, solo owner puede eliminarlo
                author_role = None
            
            # Verificar permisos
            user_role = member.role
            is_author = request.user.id == message.author.id
            
            # 🔹 Caso 1: El autor siempre puede eliminar su propio mensaje
            if is_author:
                message.delete()
                return Response(
                    {'message': 'Mensaje eliminado correctamente'},
                    status=status.HTTP_200_OK
                )
            
            # 🔹 Caso 2: Owner puede eliminar cualquier mensaje
            if user_role == WorkspaceMember.Role.OWNER:
                message.delete()
                return Response(
                    {'message': 'Mensaje eliminado correctamente'},
                    status=status.HTTP_200_OK
                )
            
            # 🔹 Caso 3: Admin puede eliminar mensajes de miembros (role='member')
            if user_role == WorkspaceMember.Role.ADMIN:
                # Admin NO puede eliminar mensajes de Owner
                if author_role == WorkspaceMember.Role.OWNER:
                    return Response(
                        {'error': 'No puedes eliminar mensajes del owner del workspace'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Admin NO puede eliminar mensajes de otros admins
                if author_role == WorkspaceMember.Role.ADMIN:
                    return Response(
                        {'error': 'No puedes eliminar mensajes de otros administradores'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Admin puede eliminar mensajes de miembros (role='member')
                if author_role == WorkspaceMember.Role.MEMBER:
                    message.delete()
                    return Response(
                        {'message': 'Mensaje eliminado correctamente'},
                        status=status.HTTP_200_OK
                    )
                
                # Si el autor ya no es miembro (rol None)
                if author_role is None:
                    message.delete()
                    return Response(
                        {'message': 'Mensaje eliminado correctamente'},
                        status=status.HTTP_200_OK
                    )
            
            # 🔹 Caso 4: Member no puede eliminar mensajes de otros
            return Response(
                {'error': 'No tienes permiso para eliminar este mensaje'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        except Message.DoesNotExist:
            return Response(
                {'error': 'Mensaje no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Channel.DoesNotExist:
            return Response(
                {'error': 'Canal no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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