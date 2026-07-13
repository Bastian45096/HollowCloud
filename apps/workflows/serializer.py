"""
Serializers para la aplicación workflows.

Responsabilidades:
- Serializar workflows con sus nodos anidados
- Serializar ejecuciones de workflows (WorkflowRun)
- Serializar ejecuciones de tareas (TaskRun)
- Validar datos de entrada para ejecución
"""

from rest_framework import serializers
from django.db import transaction

from .models import Workflow, WorkflowNode, WorkflowRun, TaskRun
from apps.chat.models import Workspace


# ============================================================
# SERIALIZERS DE NODOS
# ============================================================

class WorkflowNodeSerializer(serializers.ModelSerializer):
    """
    Serializer para nodos de workflow.
    """
    
    class Meta:
        model = WorkflowNode
        fields = [
            'id',
            'workflow',
            'name',
            'task_type',
            'config',
            'order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'workflow']


class WorkflowNodeCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear/actualizar nodos.
    """
    
    class Meta:
        model = WorkflowNode
        fields = [
            'id',
            'name',
            'task_type',
            'config',
            'order',
        ]
        read_only_fields = ['id']


# ============================================================
# SERIALIZERS DE WORKFLOWS
# ============================================================

class WorkflowSerializer(serializers.ModelSerializer):
    """
    Serializer principal para workflows con nodos anidados.
    """
    
    nodes = WorkflowNodeSerializer(many=True, read_only=True)
    nodes_count = serializers.SerializerMethodField()
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Workflow
        fields = [
            'id',
            'workspace',
            'workspace_name',
            'created_by',
            'created_by_name',
            'name',
            'description',
            'status',
            'nodes',
            'nodes_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_nodes_count(self, obj):
        """Obtener el número de nodos del workflow."""
        return obj.nodes.count()


class WorkflowCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear workflows con nodos.
    """
    
    nodes = WorkflowNodeCreateSerializer(many=True, required=False)
    
    class Meta:
        model = Workflow
        fields = [
            'id',
            'workspace',
            'name',
            'description',
            'status',
            'nodes',
        ]
        read_only_fields = ['id']
    
    def validate_workspace(self, value):
        """Validar que el workspace exista y esté activo."""
        if not value:
            raise serializers.ValidationError("El workspace es requerido")
        return value
    
    def validate_name(self, value):
        """Validar que el nombre no esté vacío."""
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre del workflow es requerido")
        return value.strip()
    
    def validate_status(self, value):
        """Validar que el status sea válido."""
        valid_statuses = [choice[0] for choice in Workflow.Status.choices]
        if value and value not in valid_statuses:
            raise serializers.ValidationError(f"Estado inválido. Opciones: {', '.join(valid_statuses)}")
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Crear workflow con sus nodos.
        """
        nodes_data = validated_data.pop('nodes', [])
        
        # Crear workflow
        workflow = Workflow.objects.create(**validated_data)
        
        # Crear nodos
        for node_data in nodes_data:
            WorkflowNode.objects.create(
                workflow=workflow,
                **node_data
            )
        
        return workflow


class WorkflowUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar workflows.
    """
    
    nodes = WorkflowNodeCreateSerializer(many=True, required=False)
    
    class Meta:
        model = Workflow
        fields = [
            'name',
            'description',
            'status',
            'nodes',
        ]
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Actualizar workflow y sus nodos.
        """
        nodes_data = validated_data.pop('nodes', None)
        
        # Actualizar campos del workflow
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar nodos
        if nodes_data is not None:
            # Eliminar nodos existentes
            instance.nodes.all().delete()
            
            # Crear nuevos nodos
            for node_data in nodes_data:
                WorkflowNode.objects.create(
                    workflow=instance,
                    **node_data
                )
        
        return instance


# ============================================================
# SERIALIZERS DE EJECUCIONES (RUNS)
# ============================================================

class TaskRunSerializer(serializers.ModelSerializer):
    """
    Serializer para ejecuciones de tareas.
    """
    
    node_name = serializers.CharField(source='node.name', read_only=True)
    task_type = serializers.CharField(source='node.task_type', read_only=True)
    
    class Meta:
        model = TaskRun
        fields = [
            'id',
            'workflow_run',
            'node',
            'node_name',
            'task_type',
            'status',
            'input_data',
            'output_data',
            'error_message',
            'attempt',
            'started_at',
            'finished_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkflowRunSerializer(serializers.ModelSerializer):
    """
    Serializer para ejecuciones de workflows.
    """
    
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    triggered_by_name = serializers.CharField(source='triggered_by.username', read_only=True)
    duration = serializers.SerializerMethodField()
    task_runs = TaskRunSerializer(many=True, read_only=True)
    
    class Meta:
        model = WorkflowRun
        fields = [
            'id',
            'workflow',
            'workflow_name',
            'triggered_by',
            'triggered_by_name',
            'status',
            'input_data',
            'output_data',
            'error_message',
            'started_at',
            'finished_at',
            'duration',
            'task_runs',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_duration(self, obj):
        """Calcular duración de la ejecución en segundos."""
        if obj.started_at and obj.finished_at:
            delta = obj.finished_at - obj.started_at
            return delta.total_seconds()
        return None


class WorkflowRunCreateSerializer(serializers.Serializer):
    """
    Serializer para ejecutar un workflow.
    """
    
    input_data = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Datos de entrada para el workflow"
    )
    
    def validate_input_data(self, value):
        """Validar que input_data sea un diccionario válido."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("input_data debe ser un objeto JSON")
        return value


# ============================================================
# SERIALIZERS DE ESTADÍSTICAS
# ============================================================

class WorkflowStatsSerializer(serializers.Serializer):
    """
    Serializer para estadísticas de workflows.
    """
    
    total_workflows = serializers.IntegerField()
    active_workflows = serializers.IntegerField()
    total_runs = serializers.IntegerField()
    successful_runs = serializers.IntegerField()
    failed_runs = serializers.IntegerField()


class TaskTypeInfoSerializer(serializers.Serializer):
    """
    Serializer para información de tipos de tareas disponibles.
    """
    
    task_type = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    config_schema = serializers.JSONField()


# ============================================================
# SERIALIZER PARA EJECUCIÓN DE NODO
# ============================================================

class ExecuteNodeSerializer(serializers.Serializer):
    """
    Serializer para ejecutar un nodo específico (debug/testing).
    """
    
    task_type = serializers.CharField()
    config = serializers.JSONField(default=dict)
    input_data = serializers.JSONField(default=dict)