from django.contrib import admin

from .models import TaskRun, Workflow, WorkflowNode, WorkflowRun


class WorkflowNodeInline(admin.TabularInline):
    model = WorkflowNode
    extra = 0
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
    ordering = ("order",)


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "workspace",
        "status",
        "created_by",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "name",
        "description",
        "workspace__name",
        "created_by__email",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("name",)

    inlines = [WorkflowNodeInline]


@admin.register(WorkflowNode)
class WorkflowNodeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "workflow",
        "name",
        "task_type",
        "order",
        "created_at",
    )

    list_filter = (
        "task_type",
        "created_at",
    )

    search_fields = (
        "name",
        "task_type",
        "workflow__name",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    ordering = ("workflow", "order")


@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "workflow",
        "status",
        "triggered_by",
        "started_at",
        "finished_at",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "workflow__name",
        "triggered_by__email",
        "error_message",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
    )

    ordering = ("-created_at",)


@admin.register(TaskRun)
class TaskRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "workflow_run",
        "node",
        "status",
        "attempt",
        "started_at",
        "finished_at",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "node__name",
        "workflow_run__workflow__name",
        "error_message",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
    )

    ordering = ("-created_at",)