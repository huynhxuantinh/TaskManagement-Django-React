from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import User
from apps.projects.models import Project, ProjectMember

from .models import Task, TaskStatus


class TaskUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.code", read_only=True)
    avatar_url = serializers.CharField(source="avatar", read_only=True)

    class Meta:
        model = User
        fields = ("id", "full_name", "email", "role", "avatar_url")


class TaskProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("id", "name")


class TaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatus
        fields = ("code", "name")


class TaskSerializer(serializers.ModelSerializer):
    project = TaskProjectSerializer(read_only=True)
    assignee = TaskUserSerializer(read_only=True)
    status = TaskStatusSerializer(read_only=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "project",
            "assignee",
            "status",
            "priority",
            "deadline",
            "is_overdue",
            "created_at",
        )

    def get_is_overdue(self, task) -> bool:
        return bool(
            task.deadline
            and task.deadline < timezone.localdate()
            and task.status.code != TaskStatus.Code.COMPLETED
        )


class AssigneeMembershipMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get("project") or getattr(self.instance, "project", None)
        assignee = attrs.get("assignee", getattr(self.instance, "assignee", None))
        if assignee and project and not ProjectMember.objects.filter(
            project=project, user=assignee
        ).exists():
            raise serializers.ValidationError(
                {"assignee_id": ["Người được giao phải là thành viên dự án."]}
            )
        return attrs


class TaskCreateSerializer(AssigneeMembershipMixin, serializers.ModelSerializer):
    project_id = serializers.PrimaryKeyRelatedField(
        source="project", queryset=Project.objects.filter(is_deleted=False)
    )
    assignee_id = serializers.PrimaryKeyRelatedField(
        source="assignee",
        queryset=User.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    status = serializers.SlugRelatedField(
        slug_field="code", queryset=TaskStatus.objects.all(), required=False
    )

    class Meta:
        model = Task
        fields = (
            "title",
            "description",
            "project_id",
            "assignee_id",
            "status",
            "priority",
            "deadline",
        )


class TaskUpdateSerializer(AssigneeMembershipMixin, serializers.ModelSerializer):
    assignee_id = serializers.PrimaryKeyRelatedField(
        source="assignee",
        queryset=User.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Task
        fields = ("title", "description", "assignee_id", "priority", "deadline")


class TaskStatusUpdateSerializer(serializers.Serializer):
    status = serializers.SlugRelatedField(
        slug_field="code", queryset=TaskStatus.objects.all()
    )


class TaskFilterSerializer(serializers.Serializer):
    project = serializers.IntegerField(required=False, min_value=1)
    assignee = serializers.IntegerField(required=False, min_value=1)
    status = serializers.ChoiceField(required=False, choices=TaskStatus.Code.choices)
    priority = serializers.ChoiceField(required=False, choices=Task.Priority.choices)
    deadline = serializers.DateField(required=False)


class TaskResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = TaskSerializer(read_only=True)


class TaskListDataSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    next = serializers.URLField(read_only=True, allow_null=True)
    previous = serializers.URLField(read_only=True, allow_null=True)
    results = TaskSerializer(many=True, read_only=True)


class TaskListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = TaskListDataSerializer(read_only=True)

