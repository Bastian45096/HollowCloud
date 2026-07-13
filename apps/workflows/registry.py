# apps/workflows/registry.py
"""
Registry Pattern para tareas de workflows en HollowCloud.
Permite registro, descubrimiento y gestión de tareas ejecutables.

Este registry sigue el patrón Singleton y permite:
- Registro dinámico de tareas
- Descubrimiento de tareas por nombre, categoría o tags
- Validación de schemas de entrada/salida
- Hooks de ciclo de vida (pre/post ejecución)
- Estadísticas y métricas del registry
"""

import logging
import inspect
from typing import Dict, Any, Optional, Callable, List, Type, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class TaskCategory(Enum):
    """Categorías de tareas disponibles en HollowCloud"""
    DATA = "data"
    FILE = "file"
    NOTIFICATION = "notification"
    WEBHOOK = "webhook"
    AI = "ai"
    INTEGRATION = "integration"
    UTILITY = "utility"
    CUSTOM = "custom"


@dataclass
class TaskDefinition:
    """
    Definición completa de una tarea registrada.
    
    Attributes:
        name: Nombre único de la tarea
        handler: Función o corrutina que ejecuta la tarea
        category: Categoría de la tarea
        description: Descripción de la tarea
        timeout: Timeout en segundos
        max_retries: Número máximo de reintentos
        is_async: Si la tarea es asíncrona
        requires_context: Si necesita acceso al contexto
        input_schema: Schema de validación de entrada
        output_schema: Schema de validación de salida
        metadata: Metadatos adicionales
        registered_at: Fecha de registro
        version: Versión de la tarea
        author: Autor de la tarea
        tags: Lista de etiquetas
    """
    name: str
    handler: Callable
    category: TaskCategory = TaskCategory.UTILITY
    description: Optional[str] = None
    timeout: int = 300
    max_retries: int = 3
    is_async: bool = False
    requires_context: bool = True
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte definición a diccionario para serialización"""
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "is_async": self.is_async,
            "requires_context": self.requires_context,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "metadata": self.metadata,
            "registered_at": self.registered_at.isoformat(),
            "version": self.version,
            "author": self.author,
            "tags": self.tags
        }
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Valida los inputs contra el schema definido.
        
        Returns:
            tuple: (es_válido, mensaje_error)
        """
        if not self.input_schema:
            return True, None
            
        # Validación básica de campos requeridos
        required = self.input_schema.get("required", [])
        missing = [field for field in required if field not in inputs]
        if missing:
            return False, f"Campos requeridos faltantes: {', '.join(missing)}"
        
        # Validación de tipos (básica)
        properties = self.input_schema.get("properties", {})
        for key, value in inputs.items():
            if key in properties:
                prop_type = properties[key].get("type")
                if prop_type == "string" and not isinstance(value, str):
                    return False, f"Campo '{key}' debe ser string, recibido {type(value).__name__}"
                elif prop_type == "number" and not isinstance(value, (int, float)):
                    return False, f"Campo '{key}' debe ser número, recibido {type(value).__name__}"
                elif prop_type == "boolean" and not isinstance(value, bool):
                    return False, f"Campo '{key}' debe ser booleano, recibido {type(value).__name__}"
                elif prop_type == "array" and not isinstance(value, list):
                    return False, f"Campo '{key}' debe ser array, recibido {type(value).__name__}"
                elif prop_type == "object" and not isinstance(value, dict):
                    return False, f"Campo '{key}' debe ser objeto, recibido {type(value).__name__}"
        
        return True, None


class TaskRegistry:
    """
    Registry de tareas para el motor de workflows de HollowCloud.
    
    Implementa el patrón Singleton y proporciona:
    - Registro dinámico de tareas
    - Búsqueda por nombre, categoría o tags
    - Validación de schemas
    - Hooks de ciclo de vida
    - Estadísticas y métricas
    
    Usage:
        registry = TaskRegistry()
        
        # Registrar una tarea
        registry.register_task(
            name="process_data",
            handler=my_function,
            category=TaskCategory.DATA,
            description="Procesa datos entrantes"
        )
        
        # Obtener una tarea
        handler = registry.get("process_data")
        
        # Listar todas las tareas
        tasks = registry.get_all_tasks()
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._tasks: Dict[str, TaskDefinition] = {}
            self._tasks_by_category: Dict[TaskCategory, List[str]] = {
                category: [] for category in TaskCategory
            }
            self._tasks_by_tag: Dict[str, List[str]] = {}
            
            # Hooks para eventos de tareas
            self._hooks: Dict[str, List[Callable]] = {
                'pre_execute': [],
                'post_execute': [],
                'on_error': [],
                'on_retry': []
            }
            
            # Cache para búsquedas rápidas
            self._name_cache: Dict[str, str] = {}
            
            logger.info("TaskRegistry initialized")
    
    # ============================================================
    # MÉTODOS DE REGISTRO
    # ============================================================
    
    def register_task(
        self,
        name: str,
        handler: Callable,
        category: Union[TaskCategory, str] = TaskCategory.UTILITY,
        description: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        version: str = "1.0.0",
        author: Optional[str] = None,
        tags: Optional[List[str]] = None,
        requires_context: bool = True
    ) -> None:
        """
        Registra una nueva tarea en el sistema.
        
        Args:
            name: Nombre único de la tarea
            handler: Función o corrutina que ejecuta la tarea
            category: Categoría de la tarea
            description: Descripción de la tarea
            timeout: Timeout en segundos
            max_retries: Número máximo de reintentos
            input_schema: Schema de validación de entrada (formato JSON Schema)
            output_schema: Schema de validación de salida
            metadata: Metadatos adicionales
            version: Versión de la tarea
            author: Autor de la tarea
            tags: Lista de etiquetas
            requires_context: Si necesita acceso al contexto
            
        Raises:
            ValueError: Si el nombre está vacío o el handler no es callable
        """
        if not name:
            raise ValueError("Task name cannot be empty")
            
        if not callable(handler):
            raise ValueError(f"Handler for task '{name}' must be callable")
        
        # Normalizar categoría
        if isinstance(category, str):
            try:
                category = TaskCategory(category.lower())
            except ValueError:
                raise ValueError(f"Invalid category: {category}")
        
        # Detectar si es async
        is_async = inspect.iscoroutinefunction(handler)
        
        # Validar signature
        sig = inspect.signature(handler)
        params = list(sig.parameters.keys())
        if len(params) < 1 or len(params) > 2:
            raise ValueError(
                f"Task handler must accept 1 or 2 parameters (inputs, context), "
                f"got {len(params)} for '{name}'"
            )
        
        # Crear definición
        definition = TaskDefinition(
            name=name,
            handler=handler,
            category=category,
            description=description or handler.__doc__,
            timeout=timeout,
            max_retries=max_retries,
            is_async=is_async,
            requires_context=requires_context,
            input_schema=input_schema,
            output_schema=output_schema,
            metadata=metadata or {},
            version=version,
            author=author,
            tags=tags or []
        )
        
        # Si la tarea ya existe, actualizar
        if name in self._tasks:
            logger.warning(f"Task '{name}' already registered, overriding")
            self.unregister_task(name)
        
        # Registrar
        self._tasks[name] = definition
        self._tasks_by_category[category].append(name)
        
        # Registrar por tags
        for tag in definition.tags:
            if tag not in self._tasks_by_tag:
                self._tasks_by_tag[tag] = []
            if name not in self._tasks_by_tag[tag]:
                self._tasks_by_tag[tag].append(name)
        
        # Cache de nombre (case-insensitive)
        self._name_cache[name.lower()] = name
        
        logger.info(
            f"Task '{name}' registered successfully",
            extra={
                "category": category.value,
                "is_async": is_async,
                "tags": tags,
                "version": version
            }
        )
    
    def unregister_task(self, name: str) -> bool:
        """
        Elimina una tarea del registro.
        
        Args:
            name: Nombre de la tarea a eliminar
            
        Returns:
            bool: True si fue eliminada, False si no existía
        """
        if name not in self._tasks:
            return False
        
        definition = self._tasks[name]
        
        # Remover de categorías
        if definition.category in self._tasks_by_category:
            if name in self._tasks_by_category[definition.category]:
                self._tasks_by_category[definition.category].remove(name)
        
        # Remover de tags
        for tag in definition.tags:
            if tag in self._tasks_by_tag and name in self._tasks_by_tag[tag]:
                self._tasks_by_tag[tag].remove(name)
                if not self._tasks_by_tag[tag]:
                    del self._tasks_by_tag[tag]
        
        # Remover de cache
        if name.lower() in self._name_cache:
            del self._name_cache[name.lower()]
        
        # Remover tarea
        del self._tasks[name]
        
        logger.info(f"Task '{name}' unregistered")
        return True
    
    # ============================================================
    # MÉTODOS DE OBTENCIÓN
    # ============================================================
    
    def get(self, name: str) -> Optional[Callable]:
        """
        Obtiene el handler de una tarea por nombre (case-insensitive).
        
        Args:
            name: Nombre de la tarea
            
        Returns:
            Callable: Handler de la tarea o None si no existe
        """
        definition = self.get_definition(name)
        return definition.handler if definition else None
    
    def get_definition(self, name: str) -> Optional[TaskDefinition]:
        """
        Obtiene la definición completa de una tarea (case-insensitive).
        
        Args:
            name: Nombre de la tarea
            
        Returns:
            TaskDefinition: Definición de la tarea o None
        """
        # Normalizar nombre
        normalized = name.lower()
        actual_name = self._name_cache.get(normalized)
        
        if actual_name and actual_name in self._tasks:
            return self._tasks[actual_name]
        
        if name in self._tasks:
            return self._tasks[name]
            
        return None
    
    def get_all_tasks(self) -> Dict[str, TaskDefinition]:
        """Obtiene todas las tareas registradas"""
        return self._tasks.copy()
    
    def get_task_names(self) -> List[str]:
        """Obtiene lista de nombres de todas las tareas"""
        return list(self._tasks.keys())
    
    def get_tasks_by_category(self, category: Union[TaskCategory, str]) -> List[str]:
        """Obtiene tareas de una categoría específica"""
        if isinstance(category, str):
            try:
                category = TaskCategory(category.lower())
            except ValueError:
                return []
        
        return self._tasks_by_category.get(category, []).copy()
    
    def get_tasks_by_tag(self, tag: str) -> List[str]:
        """Obtiene tareas con un tag específico"""
        return self._tasks_by_tag.get(tag, []).copy()
    
    def get_task_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información detallada de una tarea.
        
        Args:
            name: Nombre de la tarea
            
        Returns:
            Dict: Información de la tarea o None
        """
        definition = self.get_definition(name)
        if not definition:
            return None
            
        return definition.to_dict()
    
    def search_tasks(self, query: str) -> List[Dict[str, Any]]:
        """
        Busca tareas por nombre, descripción o tags.
        
        Args:
            query: Texto de búsqueda
            
        Returns:
            List[Dict]: Lista de definiciones que coinciden con su score
        """
        query = query.lower()
        results = []
        
        for name, definition in self._tasks.items():
            score = 0
            
            # Coincidencia en nombre (mayor peso)
            if query in name.lower():
                score += 10
            
            # Coincidencia en descripción
            if definition.description and query in definition.description.lower():
                score += 5
            
            # Coincidencia en tags
            for tag in definition.tags:
                if query in tag.lower():
                    score += 3
            
            if score > 0:
                results.append({
                    "name": name,
                    "definition": definition.to_dict(),
                    "score": score
                })
        
        # Ordenar por relevancia
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
    
    # ============================================================
    # MÉTODOS DE VALIDACIÓN
    # ============================================================
    
    def validate_task_inputs(self, name: str, inputs: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Valida los inputs de una tarea contra su schema.
        
        Args:
            name: Nombre de la tarea
            inputs: Inputs a validar
            
        Returns:
            tuple: (es_válido, mensaje_error)
        """
        definition = self.get_definition(name)
        if not definition:
            return False, f"Task '{name}' not found"
        
        return definition.validate_inputs(inputs)
    
    # ============================================================
    # HOOKS
    # ============================================================
    
    def register_hook(self, hook_type: str, callback: Callable) -> None:
        """
        Registra un hook para eventos del ciclo de vida de tareas.
        
        Args:
            hook_type: Tipo de hook ('pre_execute', 'post_execute', 'on_error', 'on_retry')
            callback: Función a ejecutar
            
        Raises:
            ValueError: Si el tipo de hook no es válido
        """
        if hook_type not in self._hooks:
            raise ValueError(f"Invalid hook type: {hook_type}. Valid: {list(self._hooks.keys())}")
            
        if not callable(callback):
            raise ValueError("Hook callback must be callable")
            
        self._hooks[hook_type].append(callback)
        logger.info(f"Hook registered for '{hook_type}'")
    
    async def execute_hooks(
        self, 
        hook_type: str, 
        *args, 
        **kwargs
    ) -> None:
        """
        Ejecuta todos los hooks de un tipo específico.
        
        Args:
            hook_type: Tipo de hook a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos nombrados
        """
        if hook_type not in self._hooks:
            return
            
        for hook in self._hooks[hook_type]:
            try:
                if inspect.iscoroutinefunction(hook):
                    await hook(*args, **kwargs)
                else:
                    hook(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error executing hook '{hook_type}': {e}", exc_info=True)
    
    # ============================================================
    # ESTADÍSTICAS Y MÉTRICAS
    # ============================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del registro.
        
        Returns:
            Dict: Estadísticas detalladas
        """
        total = len(self._tasks)
        by_category = {
            category.value: len(tasks) 
            for category, tasks in self._tasks_by_category.items()
        }
        
        by_tag = {
            tag: len(tasks) 
            for tag, tasks in self._tasks_by_tag.items()
        }
        
        async_count = sum(1 for t in self._tasks.values() if t.is_async)
        sync_count = total - async_count
        
        # Tareas con schemas
        with_schema = sum(1 for t in self._tasks.values() if t.input_schema)
        
        return {
            "total_tasks": total,
            "tasks_by_category": by_category,
            "tasks_by_tag": by_tag,
            "async_tasks": async_count,
            "sync_tasks": sync_count,
            "with_input_schema": with_schema,
            "total_categories": len(TaskCategory),
            "total_tags": len(self._tasks_by_tag),
            "hooks_registered": {k: len(v) for k, v in self._hooks.items()},
            "timestamp": datetime.now().isoformat()
        }
    
    def export_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Exporta todas las definiciones de tareas para documentación.
        
        Returns:
            Dict: Diccionario con todas las tareas serializadas
        """
        return {
            name: definition.to_dict()
            for name, definition in self._tasks.items()
        }
    
    # ============================================================
    # MÉTODOS DE UTILIDAD
    # ============================================================
    
    def clear(self) -> None:
        """Limpia todo el registro (útil para tests)"""
        self._tasks.clear()
        self._tasks_by_category = {category: [] for category in TaskCategory}
        self._tasks_by_tag.clear()
        self._name_cache.clear()
        logger.info("Registry cleared")
    
    def reload(self) -> None:
        """
        Recarga el registro (útil para desarrollo).
        Limpia y vuelve a registrar las tareas built-in.
        """
        self.clear()
        register_builtin_tasks()
        logger.info("Registry reloaded")
    
    def __contains__(self, name: str) -> bool:
        """Verifica si una tarea está registrada (case-insensitive)"""
        return name in self._tasks or name.lower() in self._name_cache
    
    def __len__(self) -> int:
        """Número de tareas registradas"""
        return len(self._tasks)
    
    def __iter__(self):
        """Itera sobre las tareas registradas"""
        return iter(self._tasks.items())


# ============================================================
# DECORADOR PARA REGISTRO FÁCIL
# ============================================================

def task(
    name: Optional[str] = None,
    category: Union[TaskCategory, str] = TaskCategory.UTILITY,
    description: Optional[str] = None,
    timeout: int = 300,
    max_retries: int = 3,
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    version: str = "1.0.0",
    author: Optional[str] = None,
    tags: Optional[List[str]] = None,
    requires_context: bool = True
):
    """
    Decorador para registrar funciones como tareas de HollowCloud.
    
    Usage:
        @task(
            name="process_data", 
            category="data", 
            tags=["processing", "etl"]
        )
        async def process_data(inputs: Dict, context: Any) -> Dict:
            '''Procesa datos entrantes'''
            return {"processed": True}
    
    Args:
        name: Nombre de la tarea (por defecto usa el nombre de la función)
        category: Categoría de la tarea
        description: Descripción (por defecto usa el docstring)
        timeout: Timeout en segundos
        max_retries: Número máximo de reintentos
        input_schema: Schema de validación de entrada
        output_schema: Schema de validación de salida
        metadata: Metadatos adicionales
        version: Versión de la tarea
        author: Autor de la tarea
        tags: Lista de etiquetas
        requires_context: Si necesita acceso al contexto
    """
    def decorator(func):
        task_name = name or func.__name__
        registry = TaskRegistry()
        
        # Registrar tarea
        registry.register_task(
            name=task_name,
            handler=func,
            category=category,
            description=description or func.__doc__,
            timeout=timeout,
            max_retries=max_retries,
            input_schema=input_schema,
            output_schema=output_schema,
            metadata=metadata,
            version=version,
            author=author,
            tags=tags,
            requires_context=requires_context
        )
        
        # Mantener referencia a la función original
        func._is_hollowcloud_task = True
        func._task_name = task_name
        
        return func
    return decorator


# ============================================================
# TAREAS BUILT-IN DE HOLLOWCLOUD
# ============================================================

@task(
    name="send_notification",
    category=TaskCategory.NOTIFICATION,
    description="Envía una notificación a un usuario",
    input_schema={
        "type": "object",
        "required": ["user_id", "message"],
        "properties": {
            "user_id": {"type": "string"},
            "message": {"type": "string"},
            "title": {"type": "string"},
            "notification_type": {"type": "string", "enum": ["info", "success", "warning", "error"]}
        }
    },
    tags=["notification", "communication"]
)
async def send_notification_task(inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Envía una notificación a un usuario.
    
    Inputs:
        user_id: ID del usuario destinatario
        message: Mensaje de la notificación
        title: Título de la notificación (opcional)
        notification_type: Tipo de notificación (info, success, warning, error)
    """
    from apps.notifications.services import create_notification
    
    user_id = inputs.get("user_id")
    message = inputs.get("message")
    title = inputs.get("title", "Notificación del sistema")
    notification_type = inputs.get("notification_type", "info")
    
    notification = create_notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type
    )
    
    if notification:
        return {
            "sent": True,
            "notification_id": str(notification.id),
            "user_id": user_id
        }
    else:
        return {
            "sent": False,
            "error": "Failed to send notification"
        }


@task(
    name="log_message",
    category=TaskCategory.UTILITY,
    description="Registra un mensaje en el log del sistema",
    input_schema={
        "type": "object",
        "required": ["message"],
        "properties": {
            "message": {"type": "string"},
            "level": {"type": "string", "enum": ["debug", "info", "warning", "error"]}
        }
    },
    tags=["logging", "debug"]
)
async def log_message_task(inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Registra un mensaje en el log del sistema.
    
    Inputs:
        message: Mensaje a loguear
        level: Nivel de log (debug, info, warning, error)
    """
    message = inputs.get("message")
    level = inputs.get("level", "info")
    
    log_func = getattr(logger, level, logger.info)
    log_func(f"[Workflow Task] {message}")
    
    return {
        "logged": True,
        "message": message,
        "level": level,
        "timestamp": datetime.now().isoformat()
    }


@task(
    name="http_request",
    category=TaskCategory.WEBHOOK,
    description="Realiza una solicitud HTTP a un endpoint externo",
    input_schema={
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {"type": "string"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
            "headers": {"type": "object"},
            "body": {"type": "object"},
            "timeout": {"type": "number", "minimum": 1, "maximum": 60}
        }
    },
    tags=["http", "webhook", "integration"]
)
async def http_request_task(inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Realiza una solicitud HTTP a un endpoint externo.
    
    Inputs:
        url: URL del endpoint
        method: Método HTTP (GET, POST, PUT, DELETE, PATCH)
        headers: Headers HTTP
        body: Cuerpo de la solicitud
        timeout: Timeout en segundos
    """
    import aiohttp
    
    url = inputs.get("url")
    method = inputs.get("method", "GET")
    headers = inputs.get("headers", {})
    body = inputs.get("body")
    timeout = inputs.get("timeout", 30)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                method=method,
                url=url,
                json=body if body else None,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                response_data = await response.json()
                
                return {
                    "status_code": response.status,
                    "response": response_data,
                    "success": 200 <= response.status < 300,
                    "url": url,
                    "method": method
                }
        except aiohttp.ClientError as e:
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "method": method
            }


@task(
    name="sleep",
    category=TaskCategory.UTILITY,
    description="Pausa la ejecución por un tiempo determinado",
    input_schema={
        "type": "object",
        "required": ["seconds"],
        "properties": {
            "seconds": {"type": "number", "minimum": 0, "maximum": 3600}
        }
    },
    tags=["utility", "delay"]
)
async def sleep_task(inputs: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Pausa la ejecución por un tiempo determinado.
    
    Inputs:
        seconds: Segundos a pausar
    """
    seconds = inputs.get("seconds", 1)
    await asyncio.sleep(seconds)
    
    return {
        "slept": seconds,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# REGISTRO DE TAREAS BUILT-IN
# ============================================================

def register_builtin_tasks() -> None:
    """
    Registra todas las tareas built-in de HollowCloud.
    Esta función debe llamarse al iniciar la aplicación.
    """
    registry = TaskRegistry()
    
    # Las tareas ya se registran mediante decoradores
    # Este método es útil para tareas que no pueden usar decoradores
    
    logger.info("Built-in tasks registered successfully")


# ============================================================
# SINGLETON PARA USO GLOBAL
# ============================================================

_registry_instance: Optional[TaskRegistry] = None


def get_task_registry() -> TaskRegistry:
    """
    Obtiene la instancia singleton del registry.
    
    Returns:
        TaskRegistry: Instancia única del registry
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = TaskRegistry()
        register_builtin_tasks()
    return _registry_instance