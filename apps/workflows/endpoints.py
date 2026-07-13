# apps/workflows/endpoints.py

"""
Endpoints para la aplicación workflows.

Responsabilidades:
- CRUD de workflows
- Ejecutar workflows
- Obtener historial de ejecuciones
- Obtener estadísticas
- Listar tipos de tareas disponibles
"""

import logging
from uuid import UUID

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.common.exceptions import PermissionDeniedError
from apps.chat.models import Workspace

from .models import Workflow, WorkflowRun, TaskRun
from .serializers import (
    WorkflowSerializer,
    WorkflowCreateSerializer,
    WorkflowUpdateSerializer,
    WorkflowRunSerializer,
    TaskRunSerializer,
    WorkflowStatsSerializer,
    TaskTypeInfoSerializer,
    ExecuteNodeSerializer,
    WorkflowRunCreateSerializer,
)
from .services import (
    create_workflow,
    update_workflow,
    delete_workflow,
    execute_workflow,
    retry_task_run,
    cancel_workflow_run,
)
from .selectors import (
    get_workspace_workflows,
    get_workflow_by_id,
    get_workflow_runs,
    get_task_runs,
    get_workflow_stats,
    get_available_task_types,
)
from .registry import TaskRegistry

logger = logging.getLogger(__name__)


# ============================================================
# WORKFLOW ENDPOINTS
# ============================================================

class WorkflowListView(APIView):
    """
    Listar workflows de un workspace.
    
    GET /api/workflows/?workspace_id={uuid}
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        
        if not workspace_id:
            return Response(
                {'error': 'workspace_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            workspace_id = UUID(workspace_id)
        except ValueError:
            return Response(
                {'error': 'workspace_id inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que el usuario sea miembro del workspace
        from apps.chat.selectors import is_workspace_member
        if not is_workspace_member(workspace_id=workspace_id, user=request.user):
            return Response(
                {'error': 'No eres miembro de este workspace'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        workflows = get_workspace_workflows(
            workspace_id=workspace_id,
            user=request.user,
        )
        
        serializer = WorkflowSerializer(workflows, many=True)
        return Response(serializer.data)


class WorkflowCreateView(APIView):
    """
    Crear un nuevo workflow.
    
    POST /api/workflows/
    Body: { "workspace_id": "uuid", "name": "Mi workflow", "nodes": [...] }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logger.info("=" * 60)
        logger.info("INICIO [WorkflowCreateView] - Creando workflow")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info("=" * 60)

        # Validar workspace
        workspace_id = request.data.get('workspace_id')
        if not workspace_id:
            return Response(
                {'error': 'workspace_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return Response(
                {'error': 'Workspace no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar permisos
        from apps.chat.selectors import is_workspace_member
        if not is_workspace_member(workspace_id=workspace.id, user=request.user):
            return Response(
                {'error': 'No eres miembro de este workspace'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validar datos
        serializer = WorkflowCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Crear workflow
            workflow = create_workflow(
                workspace_id=workspace.id,
                created_by=request.user,
                name=serializer.validated_data['name'],
                description=serializer.validated_data.get('description', ''),
                status=serializer.validated_data.get('status', Workflow.Status.DRAFT),
                nodes=serializer.validated_data.get('nodes', []),
            )
            
            response_serializer = WorkflowSerializer(workflow)
            
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [WorkflowCreateView] - Workflow creado: {workflow.id}")
            logger.info("=" * 60)
            
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"ERROR [WorkflowCreateView] - {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkflowDetailView(APIView):
    """
    Obtener, actualizar o eliminar un workflow.
    
    GET /api/workflows/{id}/
    PUT /api/workflows/{id}/
    DELETE /api/workflows/{id}/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, workflow_id: UUID):
        """Obtener workflow por ID."""
        logger.info(f"INICIO [WorkflowDetailView] - Obteniendo workflow {workflow_id}")
        
        try:
            workflow = get_workflow_by_id(workflow_id=workflow_id, user=request.user)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = WorkflowSerializer(workflow)
        return Response(serializer.data)

    def put(self, request, workflow_id: UUID):
        """Actualizar workflow completamente."""
        logger.info("=" * 60)
        logger.info("INICIO [WorkflowDetailView] - Actualizando workflow")
        logger.info(f"Workflow ID: {workflow_id}")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info("=" * 60)

        try:
            workflow = get_workflow_by_id(workflow_id=workflow_id, user=request.user)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = WorkflowUpdateSerializer(workflow, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            updated_workflow = update_workflow(
                workflow_id=workflow.id,
                user=request.user,
                name=serializer.validated_data.get('name'),
                description=serializer.validated_data.get('description'),
                status=serializer.validated_data.get('status'),
                nodes=serializer.validated_data.get('nodes'),
            )
            
            response_serializer = WorkflowSerializer(updated_workflow)
            
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [WorkflowDetailView] - Workflow actualizado: {workflow_id}")
            logger.info("=" * 60)
            
            return Response(response_serializer.data)
            
        except Exception as e:
            logger.error(f"ERROR [WorkflowDetailView] - {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def delete(self, request, workflow_id: UUID):
        """Eliminar workflow."""
        logger.info("=" * 60)
        logger.info("INICIO [WorkflowDetailView] - Eliminando workflow")
        logger.info(f"Workflow ID: {workflow_id}")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info("=" * 60)

        try:
            workflow = get_workflow_by_id(workflow_id=workflow_id, user=request.user)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            delete_workflow(
                workflow_id=workflow.id,
                user=request.user,
            )
            
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [WorkflowDetailView] - Workflow eliminado: {workflow_id}")
            logger.info("=" * 60)
            
            return Response(
                {'message': 'Workflow eliminado exitosamente'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Exception as e:
            logger.error(f"ERROR [WorkflowDetailView] - {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================
# WORKFLOW EXECUTION ENDPOINTS
# ============================================================

class WorkflowExecuteView(APIView):
    """
    Ejecutar un workflow.
    
    POST /api/workflows/{id}/execute/
    Body: { "input_data": { ... } }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, workflow_id: UUID):
        logger.info("=" * 60)
        logger.info("INICIO [WorkflowExecuteView] - Ejecutando workflow")
        logger.info(f"Workflow ID: {workflow_id}")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info("=" * 60)

        try:
            workflow = get_workflow_by_id(workflow_id=workflow_id, user=request.user)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validar datos de entrada
        serializer = WorkflowRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            workflow_run = execute_workflow(
                workflow_id=workflow.id,
                triggered_by=request.user,
                input_data=serializer.validated_data.get('input_data', {}),
            )
            
            response_serializer = WorkflowRunSerializer(workflow_run)
            
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [WorkflowExecuteView] - Workflow ejecutado: {workflow_run.id}")
            logger.info("=" * 60)
            
            return Response(
                response_serializer.data,
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"ERROR [WorkflowExecuteView] - {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================
# WORKFLOW RUNS ENDPOINTS
# ============================================================

class WorkflowRunsView(APIView):
    """
    Listar ejecuciones de un workflow.
    
    GET /api/workflows/{id}/runs/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, workflow_id: UUID):
        logger.info(f"INICIO [WorkflowRunsView] - Listando ejecuciones de workflow {workflow_id}")

        try:
            workflow = get_workflow_by_id(workflow_id=workflow_id, user=request.user)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        
        result = get_workflow_runs(
            workflow_id=workflow.id,
            limit=limit,
            offset=offset,
        )
        
        serializer = WorkflowRunSerializer(result['runs'], many=True)
        
        return Response({
            'runs': serializer.data,
            'total': result['total'],
            'limit': result['limit'],
            'offset': result['offset'],
        })


class WorkflowRunDetailView(APIView):
    """
    Obtener detalle de una ejecución específica.
    
    GET /api/workflows/runs/{id}/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, run_id: UUID):
        logger.info(f"INICIO [WorkflowRunDetailView] - Obteniendo ejecución {run_id}")

        try:
            workflow_run = WorkflowRun.objects.get(id=run_id)
        except WorkflowRun.DoesNotExist:
            return Response(
                {'error': 'Ejecución no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar permisos
        from apps.chat.selectors import is_workspace_member
        if not is_workspace_member(
            workspace_id=workflow_run.workflow.workspace_id,
            user=request.user
        ):
            return Response(
                {'error': 'No tienes acceso a esta ejecución'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = WorkflowRunSerializer(workflow_run)
        return Response(serializer.data)


class WorkflowRunCancelView(APIView):
    """
    Cancelar una ejecución en curso.
    
    POST /api/workflows/runs/{id}/cancel/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, run_id: UUID):
        logger.info("=" * 60)
        logger.info("INICIO [WorkflowRunCancelView] - Cancelando ejecución")
        logger.info(f"Run ID: {run_id}")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info("=" * 60)

        try:
            workflow_run = cancel_workflow_run(
                workflow_run_id=run_id,
                user=request.user,
            )
            
            serializer = WorkflowRunSerializer(workflow_run)
            
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [WorkflowRunCancelView] - Ejecución cancelada: {run_id}")
            logger.info("=" * 60)
            
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"ERROR [WorkflowRunCancelView] - {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================
# TASK RUN ENDPOINTS
# ============================================================

class TaskRunRetryView(APIView):
    """
    Reintentar una tarea fallida.
    
    POST /api/workflows/tasks/{id}/retry/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id: UUID):
        logger.info("=" * 60)
        logger.info("INICIO [TaskRunRetryView] - Reintentando tarea")
        logger.info(f"Task ID: {task_id}")
        logger.info(f"Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info("=" * 60)

        try:
            task_run = retry_task_run(
                task_run_id=task_id,
                user=request.user,
            )
            
            serializer = TaskRunSerializer(task_run)
            
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [TaskRunRetryView] - Tarea reintentada: {task_id}")
            logger.info("=" * 60)
            
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"ERROR [TaskRunRetryView] - {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================
# STATS ENDPOINTS
# ============================================================

class WorkflowStatsView(APIView):
    """
    Obtener estadísticas de workflows de un workspace.
    
    GET /api/workflows/stats/?workspace_id={uuid}
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        workspace_id = request.query_params.get('workspace_id')
        
        if not workspace_id:
            return Response(
                {'error': 'workspace_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            workspace_id = UUID(workspace_id)
        except ValueError:
            return Response(
                {'error': 'workspace_id inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar permisos
        from apps.chat.selectors import is_workspace_member
        if not is_workspace_member(workspace_id=workspace_id, user=request.user):
            return Response(
                {'error': 'No eres miembro de este workspace'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        stats = get_workflow_stats(workspace_id=workspace_id)
        
        serializer = WorkflowStatsSerializer(stats)
        return Response(serializer.data)


# ============================================================
# TASK TYPES ENDPOINTS
# ============================================================

class TaskTypesView(APIView):
    """
    Listar tipos de tareas disponibles.
    
    GET /api/workflows/task-types/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        task_types = get_available_task_types()
        
        serializer = TaskTypeInfoSerializer(task_types, many=True)
        return Response(serializer.data)


class TaskTypeDetailView(APIView):
    """
    Obtener información de un tipo de tarea específico.
    
    GET /api/workflows/task-types/{task_type}/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, task_type: str):
        task_info = TaskRegistry.get_task_info(task_type)
        
        if not task_info:
            return Response(
                {'error': f'Tarea "{task_type}" no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = TaskTypeInfoSerializer(task_info)
        return Response(serializer.data)