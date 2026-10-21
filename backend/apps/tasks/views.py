import csv
from datetime import timedelta

from django.http import HttpResponse
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.accounts.models import Role
from apps.accounts.permissions import has_role
from apps.core.api import success
from apps.projects.permissions import can_manage_project

from .models import Task, TaskChecklistItem, TaskStatus
from .serializers import (
    TaskAuditLogListResponseSerializer,
    TaskAuditLogSerializer,
    TaskChecklistItemSerializer,
    TaskCreateSerializer,
    TaskFilterSerializer,
    TaskListResponseSerializer,
    TaskResponseSerializer,
    TaskSerializer,
    TaskStatusSerializer,
    TaskStatusUpdateSerializer,
    TaskUpdateSerializer,
)
from .services import ChecklistService, TaskService
from .workflow import can_change_task_status


def task_queryset():
    return Task.objects.filter(
        is_deleted=False, project__is_deleted=False
    ).select_related(
        "project",
        "project__creator",
        "project__creator__role",
        "assignee",
        "assignee__role",
        "status",
        "parent__status",
    ).prefetch_related("checklist_items").annotate(
        unfinished_subtasks_count=Count(
            "subtasks",
            filter=Q(subtasks__is_deleted=False)
            & ~Q(subtasks__status__code=TaskStatus.Code.COMPLETED),
        )
    )


def csv_safe(value):
    value = str(value or "")
    return f"'{value}" if value.startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else value


@extend_schema_view(
    list=extend_schema(tags=["Tasks"], responses={200: TaskListResponseSerializer}),
    retrieve=extend_schema(tags=["Tasks"], responses={200: TaskResponseSerializer}),
    create=extend_schema(
        tags=["Tasks"], request=TaskCreateSerializer, responses={201: TaskResponseSerializer}
    ),
    partial_update=extend_schema(
        tags=["Tasks"], request=TaskUpdateSerializer, responses={200: TaskResponseSerializer}
    ),
    destroy=extend_schema(tags=["Tasks"], responses={204: None}),
)
class TaskViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["title", "priority", "deadline", "created_at"]
    ordering = ["-created_at", "-id"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = task_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if has_role(user, Role.Code.ADMIN):
            return self._apply_filters(queryset)
        if has_role(user, Role.Code.MANAGER):
            queryset = queryset.filter(project__memberships__user=user).distinct()
        else:
            queryset = queryset.filter(assignee=user)
        return self._apply_filters(queryset)

    def _apply_filters(self, queryset):
        mappings = {
            "project": "project_id",
            "assignee": "assignee_id",
            "status": "status__code",
            "priority": "priority",
            "deadline": "deadline",
            "deadline_from": "deadline__gte",
            "deadline_to": "deadline__lte",
        }
        special_filters = {"overdue", "due_soon"}
        raw_filters = {
            key: self.request.query_params[key]
            for key in (*mappings, *special_filters)
            if key in self.request.query_params
        }
        serializer = TaskFilterSerializer(data=raw_filters)
        serializer.is_valid(raise_exception=True)
        for parameter, value in serializer.validated_data.items():
            if parameter in mappings:
                queryset = queryset.filter(**{mappings[parameter]: value})
        today = timezone.localdate()
        if serializer.validated_data.get("overdue"):
            queryset = queryset.filter(deadline__lt=today).exclude(
                status__code=TaskStatus.Code.COMPLETED
            )
        if serializer.validated_data.get("due_soon"):
            queryset = queryset.filter(
                deadline__gte=today, deadline__lte=today + timedelta(days=3)
            ).exclude(status__code=TaskStatus.Code.COMPLETED)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(TaskSerializer(page, many=True, context={"request": request}).data)

    @extend_schema(tags=["Tasks"], responses={200: None})
    def export(self, request):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="cong-viec.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(
            ["ID", "Công việc", "Dự án", "Người thực hiện", "Trạng thái", "Ưu tiên", "Hạn hoàn thành"]
        )
        for task in self.filter_queryset(self.get_queryset()):
            writer.writerow(
                [
                    task.id,
                    csv_safe(task.title),
                    csv_safe(task.project.name),
                    csv_safe(task.assignee.full_name if task.assignee else ""),
                    csv_safe(task.status.name),
                    task.get_priority_display(),
                    task.deadline.isoformat() if task.deadline else "",
                ]
            )
        return response

    def retrieve(self, request, *args, **kwargs):
        return success(TaskSerializer(self.get_object(), context={"request": request}).data, "Lấy công việc thành công.")

    def create(self, request, *args, **kwargs):
        if not has_role(request.user, Role.Code.ADMIN, Role.Code.MANAGER):
            raise PermissionDenied("Bạn không có quyền tạo công việc.")
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data["project"]
        self._require_manager(project)
        task = TaskService.create_task(serializer.validated_data, request.user)
        task = task_queryset().get(pk=task.pk)
        return success(TaskSerializer(task, context={"request": request}).data, "Tạo công việc thành công.", 201)

    def partial_update(self, request, *args, **kwargs):
        task = self.get_object()
        self._require_manager(task.project)
        serializer = TaskUpdateSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = TaskService.update_task(task, serializer.validated_data, request.user)
        task = task_queryset().get(pk=task.pk)
        return success(TaskSerializer(task, context={"request": request}).data, "Cập nhật công việc thành công.")

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        self._require_manager(task.project)
        TaskService.delete_task(task, request.user)
        return Response(status=204)

    @extend_schema(tags=["Tasks"], responses={200: TaskAuditLogListResponseSerializer})
    def history(self, request, pk=None):
        task = self.get_object()
        queryset = task.audit_logs.select_related("actor", "actor__role")
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(TaskAuditLogSerializer(page, many=True).data)

    @extend_schema(
        tags=["Tasks"], request=TaskStatusUpdateSerializer, responses={200: TaskResponseSerializer}
    )
    def change_status(self, request, pk=None):
        task = self.get_object()
        if not can_change_task_status(task, request.user):
            raise PermissionDenied("Bạn không có quyền đổi trạng thái công việc này.")
        serializer = TaskStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = TaskService.change_status(
            task,
            serializer.validated_data["status"],
            request.user,
            serializer.validated_data.get("note", ""),
        )
        task = task_queryset().get(pk=task.pk)
        return success(TaskSerializer(task, context={"request": request}).data, "Cập nhật trạng thái thành công.")

    def _require_manager(self, project):
        if not can_manage_project(self.request.user, project):
            raise PermissionDenied("Bạn không có quyền quản lý công việc của dự án này.")


class TaskStatusListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Task metadata"], responses={200: TaskStatusSerializer(many=True)})
    def get(self, request):
        statuses = TaskStatus.objects.all()
        return success(TaskStatusSerializer(statuses, many=True).data, "Lấy trạng thái thành công.")


class TaskChecklistView(APIView):
    permission_classes = [IsAuthenticated]

    def get_task(self, request, pk, require_change=False):
        queryset = task_queryset()
        if not has_role(request.user, Role.Code.ADMIN):
            if has_role(request.user, Role.Code.MANAGER):
                queryset = queryset.filter(project__memberships__user=request.user).distinct()
            else:
                queryset = queryset.filter(assignee=request.user)
        task = get_object_or_404(queryset, pk=pk)
        if require_change and not can_change_task_status(task, request.user):
            raise PermissionDenied("Bạn không có quyền cập nhật checklist công việc này.")
        return task

    def get(self, request, pk):
        task = self.get_task(request, pk, require_change=True)
        return success(TaskChecklistItemSerializer(task.checklist_items.all(), many=True).data, "Lấy checklist thành công.")

    def post(self, request, pk):
        task = self.get_task(request, pk, require_change=True)
        serializer = TaskChecklistItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = ChecklistService.create(task.id, serializer.validated_data, request.user)
        return success(TaskChecklistItemSerializer(item).data, "Thêm mục checklist thành công.", 201)


class TaskChecklistItemView(TaskChecklistView):
    def get_item(self, request, pk, item_id, require_change=True):
        task = self.get_task(request, pk, require_change=require_change)
        return get_object_or_404(task.checklist_items, pk=item_id)

    def patch(self, request, pk, item_id):
        item = self.get_item(request, pk, item_id)
        serializer = TaskChecklistItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return success(TaskChecklistItemSerializer(serializer.save()).data, "Cập nhật checklist thành công.")

    def delete(self, request, pk, item_id):
        self.get_item(request, pk, item_id).delete()
        return Response(status=204)

