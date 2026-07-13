"""
Servicios para la aplicación workflows.

Responsabilidades:
- Crear, actualizar y eliminar workflows
- Ejecutar workflows y nodos
- Gestionar reintentos de tareas fallidas
- Registrar ejecuciones (WorkflowRun, TaskRun)
- Disparar workflows por eventos
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from django.db import transaction
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.common.exceptions import PermissionDeniedError, NotFoundError
from apps.chat.models import Workspace

from .models import Workflow, WorkflowNode, WorkflowRun, TaskRun
from .registry import TaskRegistry
from .executor import WorkflowExecutor

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTES DE CACHE
# ============================================================

CACHE_WORKFLOW_TTL = 3600  # 1 hora
CACHE_WORKFLOW_PREFIX = "workflow"


def _get_cache_key(workflow_id: UUID) -> str:
    """Generar clave de cache para workflow."""
    return f"{CACHE_WORKFLOW_PREFIX}:{workflow_id}"


def _invalidate_workflow_cache(workflow_id: UUID) -> None:
    """Invalidar cache de workflow."""
    cache_key = _get_cache_key(workflow_id)
    cache.delete(cache_key)
    logger.debug(f"Cache invalidada para workflow {workflow_id}")


# ============================================================
# WORKFLOW SERVICES
# ============================================================

@transaction.atomic
def create_workflow(
    *,
    workspace_id: UUID,
    created_by: User,
    name: str,
    description: str = '',
    status: str = Workflow.Status.DRAFT,
    nodes: Optional[List[Dict[str, Any]]] = None,
) -> Workflow:
    """
    Crear un nuevo workflow con sus nodos.
    
    Responsabilidades:
    - Validar que el workspace exista
    - Validar que el usuario tenga permisos
    - Crear el workflow
    - Crear los nodos en orden
    - Invalidar cache
    """
    logger.info("=" * 60)
    logger.info("INICIO [CreateWorkflow] - Creando workflow")
    logger.info(f"Workspace ID: {workspace_id}")
    logger.info(f"Creado por: {created_by.email} (ID: {created_by.id})")
    logger.info(f"Nombre: {name}")
    logger.info("=" * 60)

    # 1. Obtener workspace
    try:
        workspace = Workspace.objects.get(id=workspace_id)
        logger.info(f"PROCESO [CreateWorkflow] - Workspace encontrado: {workspace.name}")
    except Workspace.DoesNotExist:
        logger.error(f"ERROR [CreateWorkflow] - Workspace no encontrado: {workspace_id}")
        raise ValidationError("Workspace no encontrado")

    # 2. Validar permisos (solo owner o admin pueden crear workflows)
    from apps.chat.services import _can_manage_workspace
    if not _can_manage_workspace(user=created_by, workspace=workspace):
        logger.warning(f"WARNING [CreateWorkflow] - Usuario {created_by.email} no tiene permisos")
        raise PermissionDeniedError("No tienes permiso para crear workflows en este workspace")

    # 3. Validar nombre
    if not name or not name.strip():
        logger.warning("WARNING [CreateWorkflow] - Nombre vacío")
        raise ValidationError("El nombre del workflow es requerido")

    # 4. Validar nodos
    nodes = nodes or []
    if not nodes:
        logger.warning("WARNING [CreateWorkflow] - Workflow sin nodos")
        raise ValidationError("El workflow debe tener al menos un nodo")

    # 5. Validar que los nodos tengan orden único
    orders = [node.get('order') for node in nodes if node.get('order') is not None]
    if len(orders) != len(set(orders)):
        logger.warning("WARNING [CreateWorkflow] - Órdenes duplicadas en nodos")
        raise ValidationError("Los nodos no pueden tener órdenes duplicados")

    # 6. Validar que los task_type existan en el registry
    for node_data in nodes:
        task_type = node_data.get('task_type')
        if not TaskRegistry.get_task(task_type):
            logger.warning(f"WARNING [CreateWorkflow] - Task type no existe: {task_type}")
            raise ValidationError(f"Tarea '{task_type}' no encontrada")

    try:
        # 7. Crear workflow
        logger.info("PROCESO [CreateWorkflow] - Creando workflow en BD")
        workflow = Workflow.objects.create(
            workspace=workspace,
            created_by=created_by,
            name=name.strip(),
            description=description.strip() if description else '',
            status=status,
        )

        # 8. Crear nodos
        logger.info(f"PROCESO [CreateWorkflow] - Creando {len(nodes)} nodos")
        for node_data in nodes:
            WorkflowNode.objects.create(
                workflow=workflow,
                name=node_data.get('name', 'Nodo sin nombre'),
                task_type=node_data.get('task_type'),
                config=node_data.get('config', {}),
                order=node_data.get('order', 0),
            )

        # 9. Invalidar cache
        _invalidate_workflow_cache(workflow.id)

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [CreateWorkflow] - Workflow creado: {workflow.name} (ID: {workflow.id})")
        logger.info("=" * 60)

        return workflow

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [CreateWorkflow] - Error al crear workflow")
        logger.error(f"ERROR [CreateWorkflow] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        raise


@transaction.atomic
def update_workflow(
    *,
    workflow_id: UUID,
    user: User,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    nodes: Optional[List[Dict[str, Any]]] = None,
) -> Workflow:
    """
    Actualizar un workflow y sus nodos.
    
    Responsabilidades:
    - Validar que el workflow exista
    - Validar que el usuario tenga permisos
    - Actualizar campos del workflow
    - Actualizar nodos (si se proporcionan)
    - Invalidar cache
    """
    logger.info("=" * 60)
    logger.info("INICIO [UpdateWorkflow] - Actualizando workflow")
    logger.info(f"Workflow ID: {workflow_id}")
    logger.info(f"Usuario: {user.email} (ID: {user.id})")
    logger.info("=" * 60)

    # 1. Obtener workflow
    try:
        workflow = Workflow.objects.get(id=workflow_id)
        logger.info(f"PROCESO [UpdateWorkflow] - Workflow encontrado: {workflow.name}")
    except Workflow.DoesNotExist:
        logger.error(f"ERROR [UpdateWorkflow] - Workflow no encontrado: {workflow_id}")
        raise ValidationError("Workflow no encontrado")

    # 2. Validar permisos
    from apps.chat.services import _can_manage_workspace
    if not _can_manage_workspace(user=user, workspace=workflow.workspace):
        logger.warning(f"WARNING [UpdateWorkflow] - Usuario {user.email} no tiene permisos")
        raise PermissionDeniedError("No tienes permiso para modificar este workflow")

    # 3. Validar nodos si se proporcionan
    if nodes is not None:
        if not nodes:
            logger.warning("WARNING [UpdateWorkflow] - Workflow sin nodos")
            raise ValidationError("El workflow debe tener al menos un nodo")

        # Validar órdenes únicas
        orders = [node.get('order') for node in nodes if node.get('order') is not None]
        if len(orders) != len(set(orders)):
            logger.warning("WARNING [UpdateWorkflow] - Órdenes duplicadas en nodos")
            raise ValidationError("Los nodos no pueden tener órdenes duplicados")

        # Validar task types
        for node_data in nodes:
            task_type = node_data.get('task_type')
            if not TaskRegistry.get_task(task_type):
                logger.warning(f"WARNING [UpdateWorkflow] - Task type no existe: {task_type}")
                raise ValidationError(f"Tarea '{task_type}' no encontrada")

    try:
        # 4. Actualizar campos del workflow
        if name is not None:
            if not name.strip():
                logger.warning("WARNING [UpdateWorkflow] - Nombre vacío")
                raise ValidationError("El nombre no puede estar vacío")
            workflow.name = name.strip()
            logger.info(f"PROCESO [UpdateWorkflow] - Nombre actualizado a: {workflow.name}")

        if description is not None:
            workflow.description = description.strip() if description else ''
            logger.info("PROCESO [UpdateWorkflow] - Descripción actualizada")

        if status is not None:
            valid_statuses = [choice[0] for choice in Workflow.Status.choices]
            if status not in valid_statuses:
                logger.warning(f"WARNING [UpdateWorkflow] - Status inválido: {status}")
                raise ValidationError(f"Estado inválido. Opciones: {', '.join(valid_statuses)}")
            workflow.status = status
            logger.info(f"PROCESO [UpdateWorkflow] - Status actualizado a: {status}")

        workflow.save()

        # 5. Actualizar nodos si se proporcionan
        if nodes is not None:
            logger.info(f"PROCESO [UpdateWorkflow] - Actualizando {len(nodes)} nodos")
            # Eliminar nodos existentes
            workflow.nodes.all().delete()
            # Crear nuevos nodos
            for node_data in nodes:
                WorkflowNode.objects.create(
                    workflow=workflow,
                    name=node_data.get('name', 'Nodo sin nombre'),
                    task_type=node_data.get('task_type'),
                    config=node_data.get('config', {}),
                    order=node_data.get('order', 0),
                )

        # 6. Invalidar cache
        _invalidate_workflow_cache(workflow.id)

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [UpdateWorkflow] - Workflow actualizado: {workflow.id}")
        logger.info("=" * 60)

        return workflow

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [UpdateWorkflow] - Error al actualizar workflow")
        logger.error(f"ERROR [UpdateWorkflow] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        raise


@transaction.atomic
def delete_workflow(
    *,
    workflow_id: UUID,
    user: User,
) -> None:
    """
    Eliminar un workflow.
    
    Responsabilidades:
    - Validar que el workflow exista
    - Validar que el usuario tenga permisos
    - Eliminar el workflow (cascada elimina nodos y runs)
    - Invalidar cache
    """
    logger.info("=" * 60)
    logger.info("INICIO [DeleteWorkflow] - Eliminando workflow")
    logger.info(f"Workflow ID: {workflow_id}")
    logger.info(f"Usuario: {user.email} (ID: {user.id})")
    logger.info("=" * 60)

    # 1. Obtener workflow
    try:
        workflow = Workflow.objects.get(id=workflow_id)
        logger.info(f"PROCESO [DeleteWorkflow] - Workflow encontrado: {workflow.name}")
    except Workflow.DoesNotExist:
        logger.error(f"ERROR [DeleteWorkflow] - Workflow no encontrado: {workflow_id}")
        raise ValidationError("Workflow no encontrado")

    # 2. Validar permisos
    from apps.chat.services import _can_manage_workspace
    if not _can_manage_workspace(user=user, workspace=workflow.workspace):
        logger.warning(f"WARNING [DeleteWorkflow] - Usuario {user.email} no tiene permisos")
        raise PermissionDeniedError("No tienes permiso para eliminar este workflow")

    try:
        # 3. Invalidar cache antes de eliminar
        _invalidate_workflow_cache(workflow.id)

        # 4. Eliminar workflow (cascada elimina nodos y runs)
        workflow_name = workflow.name
        workflow.delete()

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [DeleteWorkflow] - Workflow eliminado: {workflow_name}")
        logger.info("=" * 60)

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [DeleteWorkflow] - Error al eliminar workflow")
        logger.error(f"ERROR [DeleteWorkflow] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        raise


# ============================================================
# WORKFLOW EXECUTION SERVICES
# ============================================================

@transaction.atomic
def execute_workflow(
    *,
    workflow_id: UUID,
    triggered_by: Optional[User] = None,
    input_data: Optional[Dict[str, Any]] = None,
) -> WorkflowRun:
    """
    Ejecutar un workflow.
    
    Responsabilidades:
    - Validar que el workflow exista y esté activo
    - Crear un WorkflowRun
    - Ejecutar el workflow con el WorkflowExecutor
    - Registrar el resultado
    - Enviar notificaciones
    """
    logger.info("=" * 60)
    logger.info("INICIO [ExecuteWorkflow] - Ejecutando workflow")
    logger.info(f"Workflow ID: {workflow_id}")
    logger.info(f"Triggered by: {triggered_by.email if triggered_by else 'Sistema'}")
    logger.info("=" * 60)

    # 1. Obtener workflow
    try:
        workflow = Workflow.objects.get(id=workflow_id)
        logger.info(f"PROCESO [ExecuteWorkflow] - Workflow encontrado: {workflow.name}")
    except Workflow.DoesNotExist:
        logger.error(f"ERROR [ExecuteWorkflow] - Workflow no encontrado: {workflow_id}")
        raise ValidationError("Workflow no encontrado")

    # 2. Validar que el workflow esté activo
    if workflow.status != Workflow.Status.ACTIVE:
        logger.warning(f"WARNING [ExecuteWorkflow] - Workflow no activo: {workflow.status}")
        raise ValidationError(f"El workflow no está activo (estado: {workflow.status})")

    # 3. Validar que tenga nodos
    nodes = workflow.nodes.all()
    if not nodes:
        logger.warning("WARNING [ExecuteWorkflow] - Workflow sin nodos")
        raise ValidationError("El workflow no tiene nodos para ejecutar")

    try:
        # 4. Crear WorkflowRun
        logger.info("PROCESO [ExecuteWorkflow] - Creando WorkflowRun")
        workflow_run = WorkflowRun.objects.create(
            workflow=workflow,
            triggered_by=triggered_by,
            status=WorkflowRun.Status.PENDING,
            input_data=input_data or {},
            started_at=timezone.now(),
        )

        # 5. Ejecutar el workflow
        logger.info("PROCESO [ExecuteWorkflow] - Iniciando WorkflowExecutor")
        executor = WorkflowExecutor(workflow_run)
        executor.execute()

        # 6. Actualizar estado final
        workflow_run.refresh_from_db()
        
        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [ExecuteWorkflow] - Workflow ejecutado: {workflow_run.id} - Estado: {workflow_run.status}")
        logger.info("=" * 60)

        # 7. Enviar notificación
        try:
            from apps.notifications.services import notify_workflow_completed, notify_workflow_failed
            
            if workflow_run.status == WorkflowRun.Status.SUCCESS:
                notify_workflow_completed(
                    user=triggered_by or workflow.created_by,
                    workflow_name=workflow.name,
                    workflow_run_id=workflow_run.id,
                )
            elif workflow_run.status == WorkflowRun.Status.FAILED:
                notify_workflow_failed(
                    user=triggered_by or workflow.created_by,
                    workflow_name=workflow.name,
                    workflow_run_id=workflow_run.id,
                    error=workflow_run.error_message,
                )
        except Exception as e:
            logger.error(f"Error al enviar notificación de workflow: {e}")

        return workflow_run

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [ExecuteWorkflow] - Error al ejecutar workflow")
        logger.error(f"ERROR [ExecuteWorkflow] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        
        # Actualizar estado a failed si no se hizo
        if workflow_run:
            workflow_run.status = WorkflowRun.Status.FAILED
            workflow_run.error_message = str(exc)
            workflow_run.finished_at = timezone.now()
            workflow_run.save()
        
        raise


@transaction.atomic
def retry_task_run(
    *,
    task_run_id: UUID,
    user: User,
) -> TaskRun:
    """
    Reintentar una tarea fallida.
    
    Responsabilidades:
    - Validar que la tarea exista y haya fallado
    - Incrementar el contador de intentos
    - Volver a ejecutar la tarea
    """
    logger.info("=" * 60)
    logger.info("INICIO [RetryTaskRun] - Reintentando tarea")
    logger.info(f"TaskRun ID: {task_run_id}")
    logger.info(f"Usuario: {user.email} (ID: {user.id})")
    logger.info("=" * 60)

    # 1. Obtener TaskRun
    try:
        task_run = TaskRun.objects.get(id=task_run_id)
        logger.info(f"PROCESO [RetryTaskRun] - TaskRun encontrado: {task_run.node.name}")
    except TaskRun.DoesNotExist:
        logger.error(f"ERROR [RetryTaskRun] - TaskRun no encontrado: {task_run_id}")
        raise ValidationError("Tarea no encontrada")

    # 2. Validar que esté fallida
    if task_run.status != TaskRun.Status.FAILED:
        logger.warning(f"WARNING [RetryTaskRun] - Tarea no fallida: {task_run.status}")
        raise ValidationError(f"Solo se pueden reintentar tareas fallidas (estado: {task_run.status})")

    # 3. Validar permisos (el usuario debe ser admin/owner o el que ejecutó el workflow)
    workflow_run = task_run.workflow_run
    if workflow_run.triggered_by and workflow_run.triggered_by.id != user.id:
        from apps.chat.services import _can_manage_workspace
        if not _can_manage_workspace(user=user, workspace=workflow_run.workflow.workspace):
            logger.warning(f"WARNING [RetryTaskRun] - Usuario {user.email} no tiene permisos")
            raise PermissionDeniedError("No tienes permiso para reintentar esta tarea")

    try:
        # 4. Incrementar intento
        task_run.attempt += 1
        task_run.status = TaskRun.Status.PENDING
        task_run.error_message = ''
        task_run.started_at = None
        task_run.finished_at = None
        task_run.save()

        # 5. Re-ejecutar la tarea
        from .executor import execute_single_task
        result = execute_single_task(task_run)

        logger.info("=" * 60)
        logger.info(f"FIN EXITOSO [RetryTaskRun] - Tarea reintentada: {task_run.id} - Estado: {task_run.status}")
        logger.info("=" * 60)

        return task_run

    except Exception as exc:
        logger.error("=" * 60)
        logger.error(f"ERROR [RetryTaskRun] - Error al reintentar tarea")
        logger.error(f"ERROR [RetryTaskRun] - Motivo: {str(exc)}")
        logger.error("=" * 60, exc_info=True)
        raise


def cancel_workflow_run(
    *,
    workflow_run_id: UUID,
    user: User,
) -> WorkflowRun:
    """
    Cancelar una ejecución de workflow en curso.
    """
    logger.info("=" * 60)
    logger.info("INICIO [CancelWorkflowRun] - Cancelando workflow run")
    logger.info(f"WorkflowRun ID: {workflow_run_id}")
    logger.info(f"Usuario: {user.email} (ID: {user.id})")
    logger.info("=" * 60)

    try:
        workflow_run = WorkflowRun.objects.get(id=workflow_run_id)
    except WorkflowRun.DoesNotExist:
        logger.error(f"ERROR [CancelWorkflowRun] - WorkflowRun no encontrado: {workflow_run_id}")
        raise ValidationError("Ejecución no encontrada")

    if workflow_run.status not in [WorkflowRun.Status.PENDING, WorkflowRun.Status.RUNNING]:
        logger.warning(f"WARNING [CancelWorkflowRun] - No se puede cancelar: {workflow_run.status}")
        raise ValidationError(f"No se puede cancelar una ejecución en estado {workflow_run.status}")

    # Validar permisos
    if workflow_run.triggered_by and workflow_run.triggered_by.id != user.id:
        from apps.chat.services import _can_manage_workspace
        if not _can_manage_workspace(user=user, workspace=workflow_run.workflow.workspace):
            raise PermissionDeniedError("No tienes permiso para cancelar esta ejecución")

    workflow_run.status = WorkflowRun.Status.FAILED
    workflow_run.error_message = "Cancelado por el usuario"
    workflow_run.finished_at = timezone.now()
    workflow_run.save()

    logger.info("=" * 60)
    logger.info(f"FIN EXITOSO [CancelWorkflowRun] - WorkflowRun cancelado: {workflow_run_id}")
    logger.info("=" * 60)

    return workflow_run


# ============================================================
# EVENT TRIGGER SERVICES
# ============================================================

def trigger_workflow_by_event(
    *,
    event_type: str,
    workspace_id: UUID,
    context: Dict[str, Any],
    triggered_by: Optional[User] = None,
) -> List[WorkflowRun]:
    """
    Disparar workflows que coinciden con un evento.
    
    Responsabilidades:
    - Buscar workflows activos que escuchen el evento
    - Ejecutar cada workflow con el contexto proporcionado
    """
    logger.info("=" * 60)
    logger.info("INICIO [TriggerWorkflowByEvent] - Disparando workflows por evento")
    logger.info(f"Evento: {event_type}")
    logger.info(f"Workspace ID: {workspace_id}")
    logger.info("=" * 60)

    # 1. Buscar workflows que coincidan con el evento
    # NOTA: Para simplificar, usamos el nombre del workflow como trigger
    # En una versión más avanzada, podrías tener un campo trigger_event en el modelo
    workflows = Workflow.objects.filter(
        workspace_id=workspace_id,
        status=Workflow.Status.ACTIVE,
        name__icontains=event_type.replace('_', ' '),  # Búsqueda simple
    )

    if not workflows:
        logger.info(f"INFO [TriggerWorkflowByEvent] - No se encontraron workflows para el evento: {event_type}")
        return []

    logger.info(f"PROCESO [TriggerWorkflowByEvent] - Encontrados {workflows.count()} workflows para el evento")

    workflow_runs = []
    for workflow in workflows:
        try:
            logger.info(f"PROCESO [TriggerWorkflowByEvent] - Ejecutando workflow: {workflow.name}")
            workflow_run = execute_workflow(
                workflow_id=workflow.id,
                triggered_by=triggered_by,
                input_data=context,
            )
            workflow_runs.append(workflow_run)
        except Exception as e:
            logger.error(f"Error al ejecutar workflow {workflow.name}: {e}")

    logger.info("=" * 60)
    logger.info(f"FIN EXITOSO [TriggerWorkflowByEvent] - {len(workflow_runs)} workflows ejecutados")
    logger.info("=" * 60)

    return workflow_runs