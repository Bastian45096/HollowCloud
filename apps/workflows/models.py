from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.chat.models import Workspace
from apps.common.models import BaseModel


class Workflow(BaseModel):
    """
    Definición de un workflow automatizado.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        DISABLED = "disabled", "Disabled"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="workflows",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_workflows",
    )
    name = models.CharField(
        max_length=255,
    )
    description = models.TextField(
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Workflow"
        verbose_name_plural = "Workflows"

    def __str__(self) -> str:
        return self.name


class WorkflowNode(BaseModel):
    """
    Nodo individual dentro de un workflow.
    """

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="nodes",
    )
    name = models.CharField(
        max_length=255,
    )
    task_type = models.CharField(
        max_length=100,
    )
    config = models.JSONField(
        default=dict,
        blank=True,
    )
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]
        verbose_name = "Workflow Node"
        verbose_name_plural = "Workflow Nodes"
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "order"],
                name="unique_workflow_node_order",
            )
        ]

    def __str__(self) -> str:
        return f"{self.workflow.name} - {self.name}"


class WorkflowRun(BaseModel):
    """
    Ejecución de un workflow.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_runs",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    input_data = models.JSONField(
        default=dict,
        blank=True,
    )
    output_data = models.JSONField(
        default=dict,
        blank=True,
    )
    error_message = models.TextField(
        blank=True,
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Workflow Run"
        verbose_name_plural = "Workflow Runs"

    def __str__(self) -> str:
        return f"{self.workflow.name} - {self.status}"


class TaskRun(BaseModel):
    """
    Ejecución individual de un nodo del workflow.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    workflow_run = models.ForeignKey(
        WorkflowRun,
        on_delete=models.CASCADE,
        related_name="task_runs",
    )
    node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name="task_runs",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    input_data = models.JSONField(
        default=dict,
        blank=True,
    )
    output_data = models.JSONField(
        default=dict,
        blank=True,
    )
    error_message = models.TextField(
        blank=True,
    )
    attempt = models.PositiveIntegerField(
        default=1,
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Task Run"
        verbose_name_plural = "Task Runs"

    def __str__(self) -> str:
        return f"{self.node.name} - {self.status}"