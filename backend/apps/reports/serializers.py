from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from apps.projects.models import Project, ProjectMember
from apps.tasks.serializers import TaskSerializer

from .models import ReportMessage


class DistributionSerializer(serializers.Serializer):
    code = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    count = serializers.IntegerField(read_only=True)


class DashboardSerializer(serializers.Serializer):
    project_count = serializers.IntegerField(read_only=True)
    task_count = serializers.IntegerField(read_only=True)
    completed_task_count = serializers.IntegerField(read_only=True)
    overdue_task_count = serializers.IntegerField(read_only=True)
    team_count = serializers.IntegerField(read_only=True)
    task_distribution = DistributionSerializer(many=True, read_only=True)
    recent_tasks = TaskSerializer(many=True, read_only=True)


class WorkloadSerializer(serializers.Serializer):
    user = UserSerializer(read_only=True)
    total_tasks = serializers.IntegerField(read_only=True)
    active_tasks = serializers.IntegerField(read_only=True)
    completed_before_deadline = serializers.IntegerField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)


class ProjectReportSerializer(serializers.Serializer):
    project_id = serializers.IntegerField(read_only=True)
    project_name = serializers.CharField(read_only=True)
    total_tasks = serializers.IntegerField(read_only=True)
    completed_tasks = serializers.IntegerField(read_only=True)
    progress = serializers.IntegerField(read_only=True)
    task_distribution = DistributionSerializer(many=True, read_only=True)


class ContributorUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)


class ContributorSerializer(serializers.Serializer):
    user = ContributorUserSerializer(read_only=True)
    completed_tasks = serializers.IntegerField(read_only=True)
    total_tasks = serializers.IntegerField(read_only=True)


class ReportMessageSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)

    class Meta:
        model = ReportMessage
        fields = (
            "id",
            "project",
            "sender",
            "receiver",
            "title",
            "content",
            "is_read",
            "created_at",
        )

    def get_project(self, message) -> dict:
        return {"id": message.project_id, "name": message.project.name}


class ReportMessageCreateSerializer(serializers.ModelSerializer):
    project_id = serializers.PrimaryKeyRelatedField(
        source="project", queryset=Project.objects.filter(is_deleted=False)
    )
    receiver_id = serializers.PrimaryKeyRelatedField(
        source="receiver", queryset=User.objects.filter(is_active=True)
    )

    class Meta:
        model = ReportMessage
        fields = ("project_id", "receiver_id", "title", "content")

    def validate(self, attrs):
        project = attrs["project"]
        receiver = attrs["receiver"]
        request = self.context["request"]
        is_admin = request.user.role.code == "ADMIN"
        if not is_admin and not ProjectMember.objects.filter(
            project=project, user=request.user
        ).exists():
            raise serializers.ValidationError(
                {"project_id": ["Bạn không phải thành viên dự án."]}
            )
        if not ProjectMember.objects.filter(project=project, user=receiver).exists():
            raise serializers.ValidationError(
                {"receiver_id": ["Người nhận phải là thành viên dự án."]}
            )
        return attrs


class DashboardResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = DashboardSerializer(read_only=True)


class WorkloadResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = WorkloadSerializer(many=True, read_only=True)


class ProjectReportResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = ProjectReportSerializer(read_only=True)


class ContributorListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = ContributorSerializer(many=True, read_only=True)


class ReportMessageResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = ReportMessageSerializer(read_only=True)


class ReportMessageListDataSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    next = serializers.URLField(read_only=True, allow_null=True)
    previous = serializers.URLField(read_only=True, allow_null=True)
    results = ReportMessageSerializer(many=True, read_only=True)


class ReportMessageListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = ReportMessageListDataSerializer(read_only=True)

