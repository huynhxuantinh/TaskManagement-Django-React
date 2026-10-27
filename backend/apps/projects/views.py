from django.db.models import Count
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.models import Role, User
from apps.accounts.permissions import has_role
from apps.core.api import failure, success
from apps.tasks.progress import project_progress_summaries

from .models import Project, ProjectMember
from .permissions import can_create_project, can_manage_project
from .serializers import (
    AddMemberSerializer,
    MemberListResponseSerializer,
    MemberResponseSerializer,
    ProjectListResponseSerializer,
    ProjectMemberSerializer,
    ProjectResponseSerializer,
    ProjectSerializer,
    ProjectWriteSerializer,
)
from .services import (
    AssignedTasksConflict,
    CreatorRemovalConflict,
    MembershipConflict,
    ProjectService,
)


def project_queryset():
    return (
        Project.objects.filter(is_deleted=False)
        .select_related("creator", "creator__role")
        .annotate(
            member_count=Count("memberships", distinct=True),
        )
    )


def attach_project_progress(projects):
    projects = list(projects)
    summaries = project_progress_summaries([project.id for project in projects])
    for project in projects:
        summary = summaries[project.id]
        project.weighted_progress = summary["progress"]
        project.missing_estimate_count = summary["missing_count"]
    return projects


@extend_schema_view(
    list=extend_schema(tags=["Projects"], responses={200: ProjectListResponseSerializer}),
    retrieve=extend_schema(tags=["Projects"], responses={200: ProjectResponseSerializer}),
    create=extend_schema(
        tags=["Projects"],
        request=ProjectWriteSerializer,
        responses={201: ProjectResponseSerializer},
    ),
    partial_update=extend_schema(
        tags=["Projects"],
        request=ProjectWriteSerializer,
        responses={200: ProjectResponseSerializer},
    ),
    destroy=extend_schema(tags=["Projects"], responses={204: None}),
)
class ProjectViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "start_date", "end_date", "created_at"]
    ordering = ["-created_at", "-id"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = project_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if has_role(user, Role.Code.ADMIN):
            return queryset
        return queryset.filter(memberships__user=user).distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = ProjectSerializer(attach_project_progress(page), many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        project = attach_project_progress([self.get_object()])[0]
        return success(ProjectSerializer(project).data, "Lấy dự án thành công.")

    def create(self, request, *args, **kwargs):
        if not can_create_project(request.user):
            raise PermissionDenied("Bạn không có quyền tạo dự án.")
        serializer = ProjectWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_creator = serializer.validated_data.pop("creator", None)
        if requested_creator is not None and not has_role(request.user, Role.Code.ADMIN):
            raise ValidationError(
                {"creator_id": ["Chỉ quản trị viên được chọn chủ dự án."]}
            )
        project = ProjectService.create_project(
            requested_creator or request.user, serializer.validated_data
        )
        project = attach_project_progress([project_queryset().get(pk=project.pk)])[0]
        return success(ProjectSerializer(project).data, "Tạo dự án thành công.", 201)

    def partial_update(self, request, *args, **kwargs):
        project = self.get_object()
        self._require_manager(project)
        serializer = ProjectWriteSerializer(
            project, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        requested_creator = serializer.validated_data.pop("creator", None)
        if requested_creator is not None and not has_role(request.user, Role.Code.ADMIN):
            raise ValidationError(
                {"creator_id": ["Chỉ quản trị viên được chọn chủ dự án."]}
            )
        serializer.save()
        if requested_creator is not None:
            project.creator = requested_creator
            project.save(update_fields=["creator"])
            ProjectMember.objects.get_or_create(project=project, user=requested_creator)
        project = attach_project_progress([project_queryset().get(pk=project.pk)])[0]
        return success(ProjectSerializer(project).data, "Cập nhật dự án thành công.")

    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        self._require_manager(project)
        project.is_deleted = True
        project.save(update_fields=["is_deleted"])
        return Response(status=204)

    @extend_schema(
        tags=["Project members"],
        methods=["GET"],
        responses={200: MemberListResponseSerializer},
    )
    @extend_schema(
        tags=["Project members"],
        methods=["POST"],
        request=AddMemberSerializer,
        responses={201: MemberResponseSerializer},
    )
    def members(self, request, pk=None):
        project = self.get_object()
        if request.method == "GET":
            memberships = ProjectMember.objects.filter(project=project).select_related(
                "user", "user__role"
            )
            page = self.paginate_queryset(memberships)
            return self.get_paginated_response(
                ProjectMemberSerializer(page, many=True).data
            )

        self._require_manager(project)
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if "user_id" in serializer.validated_data:
            user = get_object_or_404(
                User, pk=serializer.validated_data["user_id"], is_active=True
            )
        else:
            user = get_object_or_404(
                User,
                email__iexact=serializer.validated_data["email"],
                is_active=True,
            )
        try:
            membership = ProjectService.add_member(project, user)
        except MembershipConflict:
            return failure("Người dùng đã là thành viên dự án.", status=409)
        membership = ProjectMember.objects.select_related("user", "user__role").get(
            pk=membership.pk
        )
        return success(
            ProjectMemberSerializer(membership).data,
            "Thêm thành viên thành công.",
            201,
        )

    @extend_schema(
        tags=["Project members"],
        request=None,
        responses={204: None},
    )
    def remove_member(self, request, pk=None, user_id=None):
        project = self.get_object()
        self._require_manager(project)
        try:
            removed = ProjectService.remove_member(project, int(user_id))
        except CreatorRemovalConflict:
            return failure("Không thể xóa chủ dự án khỏi thành viên.", status=409)
        except AssignedTasksConflict:
            return failure(
                "Thành viên còn công việc đang mở. Hãy chuyển giao trước khi xóa.",
                status=409,
            )
        if not removed:
            return failure("Không tìm thấy thành viên.", status=404)
        return Response(status=204)

    def _require_manager(self, project):
        if not can_manage_project(self.request.user, project):
            raise PermissionDenied("Bạn không có quyền quản lý dự án này.")
