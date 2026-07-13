# apps/workflows/executor.py
"""
Workflow Executor para HollowCloud
Maneja la ejecución de workflows, nodos y tareas con soporte para reintentos,
contexto compartido y notificaciones en tiempo real.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field

from django.utils import timezone
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async

from apps.workflows.models import (
    Workflow,
    WorkflowNode,
    WorkflowRun,
    TaskRun,
)
from apps.workflows.registry import get_task_registry
from apps.notifications.services import create_notification
from apps.common.exceptions import WorkflowExecutionError, TaskExecutionError

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """
    Contexto compartido entre nodos durante la ejecución de un workflow.
    
    Este contexto permite que los nodos compartan datos y variables entre sí,
    facilitando la creación de flujos de trabajo complejos.
    """
    workflow_run_id: str
    workflow_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=timezone.now)
    trace_id: Optional[str] = None
    node_results: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene un valor del contexto (variables o data)"""
        if key in self.variables:
            return self.variables[key]
        if key in self.data:
            return self.data[key]
        return default
    
    def set(self, key: str, value: Any) -> None:
        """Establece un valor en el contexto (variables)"""
        self.variables[key] = value
        
    def merge_data(self, data: Dict[str, Any]) -> None:
        """Fusiona datos en el contexto"""
        self.data.update(data)
    
    def set_node_result(self, node_id: str, result: Any) -> None:
        """Guarda el resultado de un nodo"""
        self.node_results[node_id] = result
        
    def get_node_result(self, node_id: str) -> Optional[Any]:
        """Obtiene el resultado de un nodo"""
        return self.node_results.get(node_id)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convierte contexto a diccionario para serialización"""
        return {
            "workflow_run_id": self.workflow_run_id,
            "workflow_id": self.workflow_id,
            "variables": self.variables,
            "data": self.data,
            "start_time": self.start_time.isoformat(),
            "trace_id": self.trace_id,
            "node_results": self.node_results
        }


class WorkflowExecutor:
    """
    Ejecutor principal de workflows de HollowCloud
    
    Características:
    - Ejecución asíncrona de workflows
    - Reintentos automáticos con backoff exponencial
    - Contexto compartido entre nodos
    - Notificaciones en tiempo real via WebSocket
    - Soporte para tareas síncronas y asíncronas
    - Cache de resultados de nodos
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        max_retries: int = 3,
        default_timeout: int = 300,
        enable_websocket: bool = True
    ):
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.default_timeout = default_timeout
        self.enable_websocket = enable_websocket
        
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.process_pool = ProcessPoolExecutor(max_workers=max_workers // 2)
        self.registry = get_task_registry()
        
        # Estado de ejecución
        self._active_runs: Dict[str, WorkflowRun] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_queue = asyncio.Queue()
        self._is_running = False
        self._worker_task: Optional[asyncio.Task] = None
        
        logger.info(
            "WorkflowExecutor initialized",
            extra={
                "max_workers": max_workers,
                "max_retries": max_retries,
                "default_timeout": default_timeout
            }
        )
    
    async def initialize(self) -> None:
        """Inicializa recursos y worker"""
        self._is_running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("WorkflowExecutor initialized successfully")
    
    async def shutdown(self) -> None:
        """Apaga el executor liberando recursos"""
        self._is_running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)
        
        logger.info("WorkflowExecutor shut down successfully")
    
    # ============================================================
    # MÉTODOS SÍNCRONOS ENVUELTOS PARA ASYNC
    # ============================================================
    
    @sync_to_async
    def _get_workflow(self, workflow_id: str) -> Workflow:
        """Obtiene un workflow por ID"""
        return Workflow.objects.select_related('workspace', 'created_by').get(id=workflow_id)
    
    @sync_to_async
    def _get_workflow_nodes(self, workflow_id: str) -> List[WorkflowNode]:
        """Obtiene los nodos de un workflow ordenados"""
        return list(WorkflowNode.objects.filter(
            workflow_id=workflow_id
        ).order_by('order'))
    
    @sync_to_async
    def _create_workflow_run(
        self,
        workflow: Workflow,
        inputs: Dict[str, Any],
        user_id: Optional[str]
    ) -> WorkflowRun:
        """Crea el registro de ejecución del workflow"""
        return WorkflowRun.objects.create(
            id=str(uuid.uuid4()),
            workflow=workflow,
            triggered_by_id=user_id,
            status=WorkflowRun.Status.PENDING,
            input_data=inputs,
            started_at=timezone.now(),
        )
    
    @sync_to_async
    def _update_workflow_status(
        self,
        workflow_run: WorkflowRun,
        status: str
    ) -> None:
        """Actualiza el estado del workflow"""
        workflow_run.status = status
        if status == WorkflowRun.Status.RUNNING and not workflow_run.started_at:
            workflow_run.started_at = timezone.now()
        workflow_run.save()
    
    @sync_to_async
    def _create_task_run(
        self,
        node: WorkflowNode,
        workflow_run: WorkflowRun,
        inputs: Dict[str, Any]
    ) -> TaskRun:
        """Crea un registro de ejecución de tarea"""
        return TaskRun.objects.create(
            id=str(uuid.uuid4()),
            workflow_run=workflow_run,
            node=node,
            status=TaskRun.Status.PENDING,
            input_data=inputs,
            attempt=1,
            started_at=timezone.now(),
        )
    
    @sync_to_async
    def _update_task_status(
        self,
        task_run: TaskRun,
        status: str,
        output_data: Optional[Dict] = None,
        error_message: Optional[str] = None,
        attempt: Optional[int] = None
    ) -> None:
        """Actualiza el estado de una tarea"""
        task_run.status = status
        if output_data is not None:
            task_run.output_data = output_data
        if error_message is not None:
            task_run.error_message = error_message
        if attempt is not None:
            task_run.attempt = attempt
        task_run.finished_at = timezone.now()
        task_run.save()
    
    @sync_to_async
    def _complete_workflow(
        self,
        workflow_run: WorkflowRun,
        output_data: Dict[str, Any]
    ) -> None:
        """Completa un workflow exitosamente"""
        workflow_run.status = WorkflowRun.Status.SUCCESS
        workflow_run.output_data = output_data
        workflow_run.finished_at = timezone.now()
        workflow_run.save()
    
    @sync_to_async
    def _fail_workflow(
        self,
        workflow_run: WorkflowRun,
        error_message: str
    ) -> None:
        """Marca un workflow como fallido"""
        workflow_run.status = WorkflowRun.Status.FAILED
        workflow_run.error_message = error_message
        workflow_run.finished_at = timezone.now()
        workflow_run.save()
    
    # ============================================================
    # MÉTODOS PRINCIPALES
    # ============================================================
    
    async def execute_workflow(
        self,
        workflow_id: str,
        inputs: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> WorkflowRun:
        """
        Ejecuta un workflow por su ID
        
        Args:
            workflow_id: ID del workflow a ejecutar
            inputs: Datos de entrada para el workflow
            user_id: ID del usuario que ejecuta
            
        Returns:
            WorkflowRun: Registro de la ejecución
            
        Raises:
            WorkflowExecutionError: Si el workflow no existe o hay error
        """
        try:
            # Obtener workflow
            workflow = await self._get_workflow(workflow_id)
            
            # Verificar que el workflow esté activo
            if workflow.status != Workflow.Status.ACTIVE:
                raise WorkflowExecutionError(
                    f"Workflow '{workflow.name}' is not active (status: {workflow.status})"
                )
            
            # Crear registro de ejecución
            workflow_run = await self._create_workflow_run(
                workflow, 
                inputs, 
                user_id
            )
            
            # Inicializar contexto
            context = ExecutionContext(
                workflow_run_id=str(workflow_run.id),
                workflow_id=str(workflow.id),
                data=inputs,
                variables={},
                trace_id=str(uuid.uuid4())
            )
            
            # Notificar inicio via WebSocket
            if self.enable_websocket:
                await self._notify_workflow_status(workflow_run, "started")
            
            # Encolar ejecución
            await self._task_queue.put({
                "type": "workflow",
                "workflow_run": workflow_run,
                "context": context,
                "workflow": workflow
            })
            
            logger.info(
                f"Workflow '{workflow.name}' (ID: {workflow.id}) queued for execution",
                extra={"workflow_run_id": workflow_run.id}
            )
            
            return workflow_run
            
        except Workflow.DoesNotExist:
            logger.error(f"Workflow {workflow_id} not found")
            raise WorkflowExecutionError(f"Workflow {workflow_id} not found")
        except Exception as e:
            logger.error(f"Failed to queue workflow: {e}", exc_info=True)
            raise WorkflowExecutionError(f"Failed to execute workflow: {str(e)}")
    
    # ============================================================
    # WORKER LOOP
    # ============================================================
    
    async def _worker_loop(self) -> None:
        """Loop principal de procesamiento de tareas"""
        while self._is_running:
            try:
                item = await self._task_queue.get()
                if item["type"] == "workflow":
                    asyncio.create_task(self._execute_workflow_async(
                        item["workflow_run"],
                        item["context"],
                        item["workflow"]
                    ))
                elif item["type"] == "task":
                    asyncio.create_task(self._execute_task_async(
                        item["task_run"],
                        item["context"],
                        item["node"]
                    ))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    # ============================================================
    # EJECUCIÓN DE WORKFLOW
    # ============================================================
    
    async def _execute_workflow_async(
        self,
        workflow_run: WorkflowRun,
        context: ExecutionContext,
        workflow: Workflow
    ) -> None:
        """Ejecuta un workflow de manera asíncrona"""
        try:
            # Actualizar estado a RUNNING
            await self._update_workflow_status(workflow_run, WorkflowRun.Status.RUNNING)
            
            # Obtener nodos en orden
            nodes = await self._get_workflow_nodes(workflow.id)
            
            if not nodes:
                # Si no hay nodos, completar directamente
                await self._complete_workflow(workflow_run, context.data)
                await self._notify_workflow_status(workflow_run, "completed")
                return
            
            # Ejecutar nodos secuencialmente
            for node in nodes:
                if not await self._should_execute_node(node, context):
                    continue
                    
                await self._execute_node(node, context, workflow_run)
            
            # Completar workflow
            await self._complete_workflow(workflow_run, context.data)
            
            # Notificar completado
            if self.enable_websocket:
                await self._notify_workflow_status(workflow_run, "completed")
            
            # Enviar notificación de éxito
            await self._send_notification(
                user_id=workflow_run.triggered_by_id,
                title=f"Workflow '{workflow.name}' completado",
                message=f"El workflow '{workflow.name}' se ejecutó exitosamente",
                notification_type="success"
            )
            
            logger.info(
                f"Workflow '{workflow.name}' completed",
                extra={"workflow_run_id": workflow_run.id}
            )
            
        except Exception as e:
            logger.error(
                f"Workflow '{workflow.name}' failed: {e}",
                extra={"workflow_run_id": workflow_run.id},
                exc_info=True
            )
            await self._fail_workflow(workflow_run, str(e))
            
            # Notificar fallo
            if self.enable_websocket:
                await self._notify_workflow_status(workflow_run, "failed")
            
            # Enviar notificación de error
            await self._send_notification(
                user_id=workflow_run.triggered_by_id,
                title=f"Workflow '{workflow.name}' falló",
                message=f"El workflow '{workflow.name}' falló: {str(e)}",
                notification_type="error"
            )
    
    # ============================================================
    # EJECUCIÓN DE NODOS
    # ============================================================
    
    async def _should_execute_node(self, node: WorkflowNode, context: ExecutionContext) -> bool:
        """
        Determina si un nodo debe ejecutarse basado en condiciones.
        
        Soporta condiciones simples como:
        - "$variable" -> verifica si la variable existe y es verdadera
        - "$variable == valor" -> comparación simple
        """
        # Si el nodo tiene configurada una condición
        if node.config and "condition" in node.config:
            condition = node.config["condition"]
            
            if isinstance(condition, str):
                # Condición simple: $variable
                if condition.startswith("$"):
                    var_name = condition[1:]
                    return bool(context.get(var_name))
                
                # Condición de comparación: $variable == valor
                if " == " in condition:
                    parts = condition.split(" == ")
                    if len(parts) == 2:
                        var_name = parts[0].strip()
                        if var_name.startswith("$"):
                            var_name = var_name[1:]
                            expected = parts[1].strip().strip('"\'')
                            return str(context.get(var_name)) == expected
            
            # Si la condición no se cumple, no ejecutar
            return False
        
        return True
    
    async def _execute_node(
        self,
        node: WorkflowNode,
        context: ExecutionContext,
        workflow_run: WorkflowRun
    ) -> None:
        """Ejecuta un nodo individual"""
        # Preparar inputs para el nodo
        inputs = node.config.get("inputs", {})
        
        # Resolver referencias al contexto
        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith("$"):
                var_name = value[1:]
                inputs[key] = context.get(var_name)
        
        # Crear registro de tarea
        task_run = await self._create_task_run(
            node,
            workflow_run,
            inputs
        )
        
        # Encolar ejecución
        await self._task_queue.put({
            "type": "task",
            "task_run": task_run,
            "context": context,
            "node": node
        })
    
    # ============================================================
    # EJECUCIÓN DE TAREAS
    # ============================================================
    
    async def _execute_task_async(
        self,
        task_run: TaskRun,
        context: ExecutionContext,
        node: WorkflowNode
    ) -> None:
        """Ejecuta una tarea específica con reintentos"""
        retries = 0
        max_retries = node.config.get("max_retries", self.max_retries)
        timeout = node.config.get("timeout", self.default_timeout)
        
        try:
            # Actualizar estado a RUNNING
            await self._update_task_status(task_run, TaskRun.Status.RUNNING)
            
            # Obtener handler registrado
            handler = self.registry.get(node.task_type)
            if not handler:
                raise TaskExecutionError(f"Task type '{node.task_type}' not found in registry")
            
            # Notificar inicio
            if self.enable_websocket:
                await self._notify_task_status(task_run, "running")
            
            # Ejecutar con reintentos
            while retries <= max_retries:
                try:
                    # Ejecutar tarea con timeout
                    result = await self._execute_with_timeout(
                        handler,
                        task_run.input_data,
                        context,
                        timeout
                    )
                    
                    # Guardar resultado exitoso
                    await self._update_task_status(
                        task_run,
                        TaskRun.Status.SUCCESS,
                        output_data=result
                    )
                    
                    # Actualizar contexto con resultado
                    context.set_node_result(str(node.id), result)
                    
                    # Notificar completado
                    if self.enable_websocket:
                        await self._notify_task_status(task_run, "completed")
                    
                    logger.info(
                        f"Task '{node.name}' completed successfully",
                        extra={"task_run_id": task_run.id}
                    )
                    return
                    
                except asyncio.TimeoutError:
                    retries += 1
                    if retries <= max_retries:
                        wait_time = 2 ** retries  # Backoff exponencial
                        logger.warning(
                            f"Task '{node.name}' timeout (attempt {retries}/{max_retries})",
                            extra={"task_run_id": task_run.id}
                        )
                        await self._update_task_status(
                            task_run,
                            TaskRun.Status.RUNNING,
                            error_message=f"Timeout, retry {retries}/{max_retries}",
                            attempt=retries + 1
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        raise TimeoutError(f"Task timed out after {max_retries} retries")
                        
                except Exception as e:
                    retries += 1
                    if retries <= max_retries:
                        wait_time = 2 ** retries  # Backoff exponencial
                        logger.warning(
                            f"Task '{node.name}' failed (attempt {retries}/{max_retries}): {e}",
                            extra={"task_run_id": task_run.id}
                        )
                        await self._update_task_status(
                            task_run,
                            TaskRun.Status.RUNNING,
                            error_message=f"Retry {retries}: {str(e)}",
                            attempt=retries + 1
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        raise
            
        except asyncio.TimeoutError:
            logger.error(
                f"Task '{node.name}' timed out permanently",
                extra={"task_run_id": task_run.id}
            )
            await self._update_task_status(
                task_run,
                TaskRun.Status.FAILED,
                error_message="Task timed out permanently"
            )
            if self.enable_websocket:
                await self._notify_task_status(task_run, "failed")
                
        except Exception as e:
            logger.error(
                f"Task '{node.name}' failed permanently: {e}",
                extra={"task_run_id": task_run.id},
                exc_info=True
            )
            await self._update_task_status(
                task_run,
                TaskRun.Status.FAILED,
                error_message=str(e)
            )
            if self.enable_websocket:
                await self._notify_task_status(task_run, "failed")
    
    async def _execute_with_timeout(
        self,
        handler: Callable,
        inputs: Dict[str, Any],
        context: ExecutionContext,
        timeout: int
    ) -> Any:
        """Ejecuta un handler con timeout"""
        if asyncio.iscoroutinefunction(handler):
            # Handler asíncrono
            return await asyncio.wait_for(
                handler(inputs, context),
                timeout=timeout
            )
        else:
            # Handler síncrono - ejecutar en thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.thread_pool,
                handler,
                inputs,
                context
            )
    
    # ============================================================
    # NOTIFICACIONES
    # ============================================================
    
    async def _send_notification(
        self,
        user_id: Optional[str],
        title: str,
        message: str,
        notification_type: str = "info"
    ) -> None:
        """Envía una notificación a un usuario"""
        if not user_id:
            return
        
        try:
            # Usar el servicio de notificaciones
            await sync_to_async(create_notification)(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type
            )
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
    
    async def _notify_workflow_status(
        self,
        workflow_run: WorkflowRun,
        status: str
    ) -> None:
        """Envía notificación de estado del workflow via WebSocket"""
        if not self.enable_websocket:
            return
            
        try:
            channel_layer = get_channel_layer()
            await channel_layer.group_send(
                f"workflow_{workflow_run.id}",
                {
                    "type": "workflow_status",
                    "status": status,
                    "workflow_run_id": str(workflow_run.id),
                    "workflow_name": workflow_run.workflow.name,
                    "timestamp": timezone.now().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send WebSocket notification: {e}")
    
    async def _notify_task_status(
        self,
        task_run: TaskRun,
        status: str
    ) -> None:
        """Envía notificación de estado de tarea via WebSocket"""
        if not self.enable_websocket:
            return
            
        try:
            channel_layer = get_channel_layer()
            await channel_layer.group_send(
                f"workflow_{task_run.workflow_run_id}",
                {
                    "type": "task_status",
                    "status": status,
                    "task_run_id": str(task_run.id),
                    "node_name": task_run.node.name,
                    "task_type": task_run.node.task_type,
                    "timestamp": timezone.now().isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send WebSocket notification: {e}")
    
    # ============================================================
    # MÉTODOS DE CONSULTA
    # ============================================================
    
    @sync_to_async
    def get_workflow_status(
        self,
        workflow_run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtiene el estado de un workflow desde la base de datos"""
        try:
            workflow_run = WorkflowRun.objects.get(id=workflow_run_id)
            return {
                "status": workflow_run.status,
                "started_at": workflow_run.started_at.isoformat() if workflow_run.started_at else None,
                "finished_at": workflow_run.finished_at.isoformat() if workflow_run.finished_at else None,
                "error_message": workflow_run.error_message,
                "output_data": workflow_run.output_data
            }
        except WorkflowRun.DoesNotExist:
            return None
    
    @sync_to_async
    def get_task_run_status(self, task_run_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el estado de una tarea desde la base de datos"""
        try:
            task_run = TaskRun.objects.select_related('node').get(id=task_run_id)
            return {
                "status": task_run.status,
                "node_name": task_run.node.name,
                "attempt": task_run.attempt,
                "started_at": task_run.started_at.isoformat() if task_run.started_at else None,
                "finished_at": task_run.finished_at.isoformat() if task_run.finished_at else None,
                "error_message": task_run.error_message,
                "output_data": task_run.output_data
            }
        except TaskRun.DoesNotExist:
            return None
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del executor"""
        return {
            "active_runs": len(self._active_runs),
            "running_tasks": len(self._running_tasks),
            "queue_size": self._task_queue.qsize(),
            "max_workers": self.max_workers,
            "thread_pool_active": self.thread_pool._work_queue.qsize(),
            "process_pool_active": self.process_pool._work_queue.qsize(),
            "timestamp": timezone.now().isoformat()
        }


# ============================================================
# SINGLETON PARA USO GLOBAL
# ============================================================

_executor_instance: Optional[WorkflowExecutor] = None


def get_workflow_executor() -> WorkflowExecutor:
    """
    Obtiene la instancia singleton del executor.
    
    Returns:
        WorkflowExecutor: Instancia única del executor
    """
    global _executor_instance
    if _executor_instance is None:
        from django.conf import settings
        
        _executor_instance = WorkflowExecutor(
            max_workers=getattr(settings, "WORKFLOW_MAX_WORKERS", 4),
            max_retries=getattr(settings, "WORKFLOW_MAX_RETRIES", 3),
            default_timeout=getattr(settings, "WORKFLOW_DEFAULT_TIMEOUT", 300),
            enable_websocket=getattr(settings, "WORKFLOW_ENABLE_WEBSOCKET", True)
        )
    return _executor_instance