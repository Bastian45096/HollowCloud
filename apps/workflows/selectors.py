# apps/workflows/selectors.py

"""
Selectors para la aplicación workflows.

Responsabilidades:
- Obtener workflows de un workspace
- Obtener workflow por ID (con permisos)
- Obtener ejecuciones de workflows (WorkflowRun)
- Obtener ejecuciones de tareas (TaskRun)
- Obtener estadísticas de workflows
- Obtener tipos de tareas disponibles
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from django.db.models import Q, Count, Avg, Sum
from django.core.cache import cache
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.chat.models import Workspace
from apps.chat.selectors import is_workspace_member

from .models import Workflow, WorkflowNode, WorkflowRun, TaskRun
from .registry import TaskRegistry

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTES DE CACHE
# ============================================================

CACHE_WORKFLOW_TTL = 3600  # 1 hora
CACHE_WORKFLOW_PREFIX = "workflow"
CACHE_WORKFLOW_LIST_TTL = 1800  # 30 minutos


def _get_workflow_cache_key(workflow_id: UUID) -> str:
    """Generar clave de cache para workflow."""
    return f"{CACHE_WORKFLOW_PREFIX}:{workflow_id}"


def _get_workflow_list_cache_key(workspace_id: UUID, user_id: UUID) -> str:
    """Generar clave de cache para lista de workflows."""
    return f"{CACHE_WORKFLOW_PREFIX}:list:{workspace_id}:{user_id}"


# ============================================================
# WORKFLOW SELECTORS
# ============================================================

def get_workspace_workflows(
    *,
    workspace_id: UUID,
    user: User,
    status: Optional[str] = None,
    use_cache: bool = True,
) -> List[Workflow]:
    """
    Obtener todos los workflows de un workspace.
    
    Args:
        workspace_id: UUID del workspace
        user: Usuario que hace la petición
        status: Filtrar por estado (draft, active, disabled)
        use_cache: Usar cache (True por defecto)
    
    Returns:
        List[Workflow]: Lista de workflows
    """
    logger.info("=" * 60)
    logger.info("INICIO [GetWorkspaceWorkflows] - Obteniendo workflows del workspace")
    logger.info(f"Workspace ID: {workspace_id}")
    logger.info(f"Usuario: {user.email} (ID: {user.id})")
    logger.info("=" * 60)

    # Verificar que el usuario sea miembro del workspace
    if not is_workspace_member(workspace_id=workspace_id, user=user):
        logger.warning(f"WARNING [GetWorkspaceWorkflows] - Usuario {user.email} no es miembro")
        return []

    try:
        # Intentar obtener de cache
        if use_cache:
            cache_key = _get_workflow_list_cache_key(workspace_id, user.id)
            workflow_ids = cache.get(cache_key)
            
            if workflow_ids is not None:
                logger.info(f"PROCESO [GetWorkspaceWorkflows] - Cache hit: {len(workflow_ids)} workflows")
                workflows = Workflow.objects.filter(
                    id__in=workflow_ids,
                    workspace_id=workspace_id
                ).select_related('workspace', 'created_by').prefetch_related('nodes')
                
                # Aplicar filtro de status si se proporciona
                if status:
                    workflows = workflows.filter(status=status)
                
                return list(workflows)

        # Cache miss: consultar base de datos
        logger.info("PROCESO [GetWorkspaceWorkflows] - Cache miss, consultando BD")
        queryset = Workflow.objects.filter(workspace_id=workspace_id)
        
        if status:
            queryset = queryset.filter(status=status)
            logger.info(f"PROCESO [GetWorkspaceWorkflows] - Filtro por status: {status}")
        
        workflows = list(
            queryset
            .select_related('workspace', 'created_by')
            .prefetch_related('nodes')
            .order_by('name')
        )

        # Guardar en cache (solo IDs para mantener cache ligera)
        if use_cache and workflows:
            workflow_ids = [str(w.id) for w in workflows]
            cache_key = _get_workflow_list_cache_key(workspace_id, user.id)
            cache.set(cache_key, workflow_ids, CACHE_WORKFLOW_LIST_TTL)
            logger.info(f"PROCESO [GetWorkspaceWorkflows] - Cache guardada: {len(workflow_ids)} workflows")

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [GetWorkspaceWorkflows] - Encontrados {len(workflows)} workflows")
        logger.info("=" * 60)

        return workflows

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [GetWorkspaceWorkflows] - Error al obtener workflows")
        logger.error(f"ERROR [GetWorkspaceWorkflows] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        return []


def get_workflow_by_id(
    *,
    workflow_id: UUID,
    user: User,
    use_cache: bool = True,
) -> Optional[Workflow]:
    """
    Obtener un workflow por su ID con verificación de permisos.
    
    Args:
        workflow_id: UUID del workflow
        user: Usuario que hace la petición
        use_cache: Usar cache (True por defecto)
    
    Returns:
        Workflow: El workflow encontrado
    
    Raises:
        ValidationError: Si el workflow no existe o el usuario no tiene permisos
    """
    logger.info("=" * 60)
    logger.info("INICIO [GetWorkflowById] - Obteniendo workflow por ID")
    logger.info(f"Workflow ID: {workflow_id}")
    logger.info(f"Usuario: {user.email} (ID: {user.id})")
    logger.info("=" * 60)

    try:
        # Intentar obtener de cache
        if use_cache:
            cache_key = _get_workflow_cache_key(workflow_id)
            workflow = cache.get(cache_key)
            
            if workflow is not None:
                logger.info(f"PROCESO [GetWorkflowById] - Cache hit: {workflow.name}")
                # Verificar permisos
                if not is_workspace_member(workspace_id=workflow.workspace_id, user=user):
                    logger.warning(f"WARNING [GetWorkflowById] - Usuario {user.email} no es miembro")
                    raise ValidationError("No tienes acceso a este workflow")
                return workflow

        # Cache miss: consultar base de datos
        logger.info("PROCESO [GetWorkflowById] - Cache miss, consultando BD")
        workflow = Workflow.objects.select_related(
            'workspace', 'created_by'
        ).prefetch_related('nodes').filter(id=workflow_id).first()

        if workflow is None:
            logger.warning(f"WARNING [GetWorkflowById] - Workflow no encontrado: {workflow_id}")
            raise ValidationError("Workflow no encontrado")

        # Verificar que el usuario sea miembro del workspace
        if not is_workspace_member(workspace_id=workflow.workspace_id, user=user):
            logger.warning(f"WARNING [GetWorkflowById] - Usuario {user.email} no es miembro")
            raise ValidationError("No tienes acceso a este workflow")

        # Guardar en cache
        if use_cache:
            cache_key = _get_workflow_cache_key(workflow_id)
            cache.set(cache_key, workflow, CACHE_WORKFLOW_TTL)
            logger.info(f"PROCESO [GetWorkflowById] - Cache guardada: {workflow_id}")

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [GetWorkflowById] - Workflow encontrado: {workflow.name}")
        logger.info("=" * 60)

        return workflow

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [GetWorkflowById] - Error al obtener workflow")
        logger.error(f"ERROR [GetWorkflowById] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        raise ValidationError(f"Error al obtener workflow: {str(exc)}")


# ============================================================
# WORKFLOW RUN SELECTORS
# ============================================================

def get_workflow_runs(
    *,
    workflow_id: UUID,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Obtener ejecuciones de un workflow con paginación.
    
    Args:
        workflow_id: UUID del workflow
        limit: Límite de resultados (por defecto 50)
        offset: Offset para paginación (por defecto 0)
        status: Filtrar por estado (pending, running, success, failed)
    
    Returns:
        Dict con runs, total, limit y offset
    """
    logger.info("=" * 60)
    logger.info("INICIO [GetWorkflowRuns] - Obteniendo ejecuciones de workflow")
    logger.info(f"Workflow ID: {workflow_id}")
    logger.info(f"Límite: {limit}, Offset: {offset}")
    logger.info(f"Status: {status}")
    logger.info("=" * 60)

    try:
        queryset = WorkflowRun.objects.filter(workflow_id=workflow_id)
        
        if status:
            queryset = queryset.filter(status=status)
            logger.info(f"PROCESO [GetWorkflowRuns] - Filtro por status: {status}")

        total = queryset.count()
        logger.info(f"PROCESO [GetWorkflowRuns] - Total ejecuciones: {total}")

        runs = list(
            queryset
            .select_related('workflow', 'triggered_by')
            .prefetch_related('task_runs')
            .order_by('-created_at')[offset:offset + limit]
        )

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [GetWorkflowRuns] - Encontradas {len(runs)} ejecuciones")
        logger.info("=" * 60)

        return {
            "runs": runs,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [GetWorkflowRuns] - Error al obtener ejecuciones")
        logger.error(f"ERROR [GetWorkflowRuns] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        raise


def get_task_runs(
    *,
    workflow_run_id: UUID,
    status: Optional[str] = None,
) -> List[TaskRun]:
    """
    Obtener ejecuciones de tareas de un workflow run.
    
    Args:
        workflow_run_id: UUID del workflow run
        status: Filtrar por estado (pending, running, success, failed)
    
    Returns:
        List[TaskRun]: Lista de ejecuciones de tareas
    """
    logger.info("=" * 60)
    logger.info("INICIO [GetTaskRuns] - Obteniendo ejecuciones de tareas")
    logger.info(f"Workflow Run ID: {workflow_run_id}")
    logger.info(f"Status: {status}")
    logger.info("=" * 60)

    try:
        queryset = TaskRun.objects.filter(workflow_run_id=workflow_run_id)
        
        if status:
            queryset = queryset.filter(status=status)
            logger.info(f"PROCESO [GetTaskRuns] - Filtro por status: {status}")

        task_runs = list(
            queryset
            .select_related('node', 'workflow_run')
            .order_by('created_at')
        )

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [GetTaskRuns] - Encontradas {len(task_runs)} tareas")
        logger.info("=" * 60)

        return task_runs

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [GetTaskRuns] - Error al obtener tareas")
        logger.error(f"ERROR [GetTaskRuns] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        raise


# ============================================================
# STATS SELECTORS
# ============================================================

def get_workflow_stats(
    *,
    workspace_id: UUID,
) -> Dict[str, Any]:
    """
    Obtener estadísticas de workflows de un workspace.
    
    Args:
        workspace_id: UUID del workspace
    
    Returns:
        Dict con estadísticas
    """
    logger.info("=" * 60)
    logger.info("INICIO [GetWorkflowStats] - Obteniendo estadísticas")
    logger.info(f"Workspace ID: {workspace_id}")
    logger.info("=" * 60)

    try:
        # Total de workflows
        total_workflows = Workflow.objects.filter(workspace_id=workspace_id).count()
        logger.info(f"PROCESO [GetWorkflowStats] - Total workflows: {total_workflows}")

        # Workflows activos
        active_workflows = Workflow.objects.filter(
            workspace_id=workspace_id,
            status=Workflow.Status.ACTIVE
        ).count()
        logger.info(f"PROCESO [GetWorkflowStats] - Workflows activos: {active_workflows}")

        # Total de ejecuciones
        total_runs = WorkflowRun.objects.filter(
            workflow__workspace_id=workspace_id
        ).count()
        logger.info(f"PROCESO [GetWorkflowStats] - Total ejecuciones: {total_runs}")

        # Ejecuciones exitosas
        successful_runs = WorkflowRun.objects.filter(
            workflow__workspace_id=workspace_id,
            status=WorkflowRun.Status.SUCCESS
        ).count()
        logger.info(f"PROCESO [GetWorkflowStats] - Ejecuciones exitosas: {successful_runs}")

        # Ejecuciones fallidas
        failed_runs = WorkflowRun.objects.filter(
            workflow__workspace_id=workspace_id,
            status=WorkflowRun.Status.FAILED
        ).count()
        logger.info(f"PROCESO [GetWorkflowStats] - Ejecuciones fallidas: {failed_runs}")

        # Tasa de éxito
        success_rate = 0
        if total_runs > 0:
            success_rate = round((successful_runs / total_runs) * 100, 2)

        logger.info("=" * 60)
        logger.info("FIN EXITOSO [GetWorkflowStats] - Estadísticas obtenidas")
        logger.info("=" * 60)

        return {
            "total_workflows": total_workflows,
            "active_workflows": active_workflows,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": success_rate,
        }

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [GetWorkflowStats] - Error al obtener estadísticas")
        logger.error(f"ERROR [GetWorkflowStats] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        return {
            "total_workflows": 0,
            "active_workflows": 0,
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "success_rate": 0,
        }


# ============================================================
# TASK TYPES SELECTORS
# ============================================================

def get_available_task_types() -> List[Dict[str, Any]]:
    """
    Obtener todos los tipos de tareas disponibles en el registro.
    
    Returns:
        List[Dict]: Lista de tipos de tareas con su información
    """
    logger.info("INICIO [GetAvailableTaskTypes] - Obteniendo tipos de tareas disponibles")

    try:
        task_types = TaskRegistry.list_tasks()
        logger.info(f"PROCESO [GetAvailableTaskTypes] - Encontrados {len(task_types)} tipos de tareas")

        result = []
        for task_type in task_types:
            task_info = TaskRegistry.get_task_info(task_type)
            if task_info:
                result.append({
                    "task_type": task_type,
                    "name": task_info.get("name", task_type),
                    "description": task_info.get("description", ""),
                    "config_schema": task_info.get("config_schema", {}),
                })

        logger.info(f"FIN EXITOSO [GetAvailableTaskTypes] - {len(result)} tipos de tareas")
        return result

    except Exception as exc:
        logger.error(f"ERROR [GetAvailableTaskTypes] - Error al obtener tipos de tareas: {str(exc)}", exc_info=True)
        return []


def get_workflow_nodes(workflow_id: UUID) -> List[WorkflowNode]:
    """
    Obtener todos los nodos de un workflow en orden.
    
    Args:
        workflow_id: UUID del workflow
    
    Returns:
        List[WorkflowNode]: Lista de nodos ordenados
    """
    logger.info(f"INICIO [GetWorkflowNodes] - Obteniendo nodos de workflow {workflow_id}")

    try:
        nodes = list(
            WorkflowNode.objects
            .filter(workflow_id=workflow_id)
            .order_by('order')
        )
        logger.info(f"PROCESO [GetWorkflowNodes] - Encontrados {len(nodes)} nodos")
        return nodes

    except Exception as exc:
        logger.error(f"ERROR [GetWorkflowNodes] - Error al obtener nodos: {str(exc)}", exc_info=True)
        return []


def get_task_run_by_id(task_run_id: UUID) -> Optional[TaskRun]:
    """
    Obtener una ejecución de tarea por su ID.
    
    Args:
        task_run_id: UUID de la ejecución de tarea
    
    Returns:
        Optional[TaskRun]: La ejecución de tarea o None si no existe
    """
    logger.info(f"INICIO [GetTaskRunById] - Obteniendo tarea {task_run_id}")

    try:
        task_run = TaskRun.objects.select_related(
            'node', 'workflow_run', 'workflow_run__workflow'
        ).filter(id=task_run_id).first()
        
        if task_run:
            logger.info(f"PROCESO [GetTaskRunById] - Tarea encontrada: {task_run.node.name}")
        else:
            logger.warning(f"WARNING [GetTaskRunById] - Tarea no encontrada: {task_run_id}")
        
        return task_run

    except Exception as exc:
        logger.error(f"ERROR [GetTaskRunById] - Error al obtener tarea: {str(exc)}", exc_info=True)
        return None