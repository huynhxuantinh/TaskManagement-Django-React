from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.permissions import has_role
from apps.core.api import success
from apps.core.pagination import StandardPagination
from apps.tasks.serializers import TaskSerializer

from .models import ReportMessage
from .serializers import (
    ContributorListResponseSerializer,
    DashboardResponseSerializer,
    ProjectReportResponseSerializer,
    ReportMessageCreateSerializer,
    ReportMessageListResponseSerializer,
    ReportMessageResponseSerializer,
    ReportMessageSerializer,
    WorkloadResponseSerializer,
)
from .services import (
    dashboard_summary,
    project_report,
    scoped_projects,
    top_contributors,
    workload,
)


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Dashboard"], responses={200: DashboardResponseSerializer})
    def get(self, request):
        data = dashboard_summary(request.user)
        data["recent_tasks"] = TaskSerializer(data["recent_tasks"], many=True).data
        return success(data, "Lấy tổng quan thành công.")


class WorkloadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Reports"], responses={200: WorkloadResponseSerializer})
    def get(self, request):
        if not has_role(request.user, Role.Code.ADMIN, Role.Code.MANAGER):
            raise PermissionDenied("Bạn không có quyền xem báo cáo khối lượng.")
        rows = [
            {
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "role": user.role.code,
                    "avatar_url": user.avatar,
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "permissions": [user.role.code],
                },
                "total_tasks": user.total_tasks,
                "active_tasks": user.active_tasks,
                "completed_before_deadline": user.completed_before_deadline,
                "is_available": user.active_tasks == 0,
            }
            for user in workload(request.user)
        ]
        return success(rows, "Lấy báo cáo khối lượng thành công.")


def get_scoped_project(user, project_id):
    return get_object_or_404(scoped_projects(user), pk=project_id)


class ProjectReportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Reports"], responses={200: ProjectReportResponseSerializer})
    def get(self, request, project_id):
        project = get_scoped_project(request.user, project_id)
        return success(project_report(project), "Lấy báo cáo dự án thành công.")


class TopContributorsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Reports"], responses={200: ContributorListResponseSerializer})
    def get(self, request, project_id):
        project = get_scoped_project(request.user, project_id)
        rows = [
            {
                "user": {
                    "id": row["user_id"],
                    "full_name": row["full_name"],
                    "email": row["email"],
                },
                "completed_tasks": row["completed_tasks"],
                "total_tasks": row["total_tasks"],
            }
            for row in top_contributors(project)
        ]
        return success(rows, "Lấy đóng góp dự án thành công.")


class ReportMessageListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, user):
        return (
            ReportMessage.objects.filter(
                Q(sender=user) | Q(receiver=user), project__is_deleted=False
            )
            .select_related(
                "project", "sender", "sender__role", "receiver", "receiver__role"
            )
            .order_by("-created_at", "-id")
        )

    @extend_schema(tags=["Report messages"], responses={200: ReportMessageListResponseSerializer})
    def get(self, request):
        paginator = StandardPagination()
        page = paginator.paginate_queryset(self.get_queryset(request.user), request)
        return paginator.get_paginated_response(
            ReportMessageSerializer(page, many=True).data
        )

    @extend_schema(
        tags=["Report messages"], request=ReportMessageCreateSerializer,
        responses={201: ReportMessageResponseSerializer}
    )
    def post(self, request):
        serializer = ReportMessageCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save(sender=request.user)
        message = self.get_queryset(request.user).get(pk=message.pk)
        return success(
            ReportMessageSerializer(message).data,
            "Gửi báo cáo thành công.",
            201,
        )


class ReportMessageReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Report messages"],
        request=None,
        responses={200: ReportMessageResponseSerializer},
    )
    def patch(self, request, pk):
        message = get_object_or_404(
            ReportMessage.objects.select_related(
                "project", "sender", "sender__role", "receiver", "receiver__role"
            ).filter(Q(sender=request.user) | Q(receiver=request.user)),
            pk=pk,
        )
        if message.receiver_id != request.user.id:
            raise PermissionDenied("Chỉ người nhận được đánh dấu đã đọc.")
        if not message.is_read:
            message.is_read = True
            message.save(update_fields=["is_read"])
        return success(
            ReportMessageSerializer(message).data,
            "Đánh dấu báo cáo đã đọc thành công.",
        )

