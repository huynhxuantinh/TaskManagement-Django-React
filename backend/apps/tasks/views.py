from django.shortcuts import get_object_or_404
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

from .models import Task, TaskStatus
from .serializers import (
    TaskCreateSerializer,
    TaskFilterSerializer,
    TaskListResponseSerializer,
    TaskResponseSerializer,
    TaskSerializer,
    TaskStatusSerializer,
    TaskStatusUpdateSerializer,
    TaskUpdateSerializer,
)
from .services import TaskService


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
    )


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
        }
        raw_filters = {
            key: self.request.query_params[key]
            for key in mappings
            if key in self.request.query_params
        }
        serializer = TaskFilterSerializer(data=raw_filters)
        serializer.is_valid(raise_exception=True)
        for parameter, value in serializer.validated_data.items():
            queryset = queryset.filter(**{mappings[parameter]: value})
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(TaskSerializer(page, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return success(TaskSerializer(self.get_object()).data, "Lấy công việc thành công.")

    def create(self, request, *args, **kwargs):
        if not has_role(request.user, Role.Code.ADMIN, Role.Code.MANAGER):
            raise PermissionDenied("Bạn không có quyền tạo công việc.")
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data["project"]
        self._require_manager(project)
        task = TaskService.create_task(serializer.validated_data)
        task = task_queryset().get(pk=task.pk)
        return success(TaskSerializer(task).data, "Tạo công việc thành công.", 201)

    def partial_update(self, request, *args, **kwargs):
        task = self.get_object()
        self._require_manager(task.project)
        serializer = TaskUpdateSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = TaskService.update_task(task, serializer.validated_data)
        task = task_queryset().get(pk=task.pk)
        return success(TaskSerializer(task).data, "Cập nhật công việc thành công.")

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        self._require_manager(task.project)
        task.is_deleted = True
        task.save(update_fields=["is_deleted"])
        return Response(status=204)

    @extend_schema(
        tags=["Tasks"], request=TaskStatusUpdateSerializer, responses={200: TaskResponseSerializer}
    )
    def change_status(self, request, pk=None):
        task = self.get_object()
        if not (
            can_manage_project(request.user, task.project)
            or task.assignee_id == request.user.id
        ):
            raise PermissionDenied("Bạn không có quyền đổi trạng thái công việc này.")
        serializer = TaskStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = TaskService.change_status(
            task, serializer.validated_data["status"], request.user
        )
        task = task_queryset().get(pk=task.pk)
        return success(TaskSerializer(task).data, "Cập nhật trạng thái thành công.")

    def _require_manager(self, project):
        if not can_manage_project(self.request.user, project):
            raise PermissionDenied("Bạn không có quyền quản lý công việc của dự án này.")


class TaskStatusListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Task metadata"], responses={200: TaskStatusSerializer(many=True)})
    def get(self, request):
        statuses = TaskStatus.objects.all()
        return success(TaskStatusSerializer(statuses, many=True).data, "Lấy trạng thái thành công.")

