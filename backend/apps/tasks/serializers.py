from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import User
from apps.projects.models import Project, ProjectMember

from .models import Task, TaskAuditLog, TaskChecklistItem, TaskStatus
from .workflow import allowed_transitions


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
    allowed_transitions = serializers.SerializerMethodField()
    effective_progress = serializers.IntegerField(read_only=True)
    parent_id = serializers.IntegerField(read_only=True, allow_null=True)

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
            "parent_id",
            "start_date",
            "estimated_hours",
            "progress",
            "effective_progress",
            "deadline",
            "is_overdue",
            "created_at",
            "updated_at",
            "completed_at",
            "allowed_transitions",
        )

    def get_is_overdue(self, task) -> bool:
        return bool(
            task.deadline
            and task.deadline < timezone.localdate()
            and task.status.code != TaskStatus.Code.COMPLETED
        )

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_allowed_transitions(self, task):
        request = self.context.get("request")
        return allowed_transitions(task, request.user) if request else []


class AssigneeMembershipMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get("project") or getattr(self.instance, "project", None)
        assignee = attrs.get("assignee", getattr(self.instance, "assignee", None))
        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        deadline = attrs.get("deadline", getattr(self.instance, "deadline", None))
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        if assignee and project and not ProjectMember.objects.filter(
            project=project, user=assignee
        ).exists():
            raise serializers.ValidationError(
                {"assignee_id": ["Người được giao phải là thành viên dự án."]}
            )
        if start_date and deadline and start_date > deadline:
            raise serializers.ValidationError({"start_date": ["Ngày bắt đầu phải trước hoặc bằng hạn hoàn thành."]})
        if parent:
            if parent.is_deleted or parent.project_id != project.id:
                raise serializers.ValidationError({"parent": ["Công việc cha phải thuộc cùng dự án và chưa bị xóa."]})
            if parent.status.code == TaskStatus.Code.COMPLETED:
                raise serializers.ValidationError({"parent": ["Hãy mở lại công việc cha trước."]})
            if parent.parent_id:
                raise serializers.ValidationError({"parent": ["Chỉ hỗ trợ một cấp công việc con."]})
            if self.instance and parent.pk == self.instance.pk:
                raise serializers.ValidationError({"parent": ["Không thể chọn chính công việc này làm cha."]})
        if self.instance and self.instance.subtasks.filter(is_deleted=False).exists() and "parent" in attrs:
            raise serializers.ValidationError({"parent": ["Công việc đang có công việc con không thể trở thành công việc con."]})
        if self.instance and self.instance.checklist_items.exists() and "progress" in attrs:
            raise serializers.ValidationError({"progress": ["Tiến độ được tính tự động từ checklist."]})
        return attrs


class TaskCreateSerializer(AssigneeMembershipMixin, serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.filter(is_deleted=False), required=False, allow_null=True
    )
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
            "parent",
            "start_date",
            "estimated_hours",
            "progress",
            "deadline",
        )


class TaskUpdateSerializer(AssigneeMembershipMixin, serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.filter(is_deleted=False), required=False, allow_null=True
    )
    assignee_id = serializers.PrimaryKeyRelatedField(
        source="assignee",
        queryset=User.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Task
        fields = ("title", "description", "assignee_id", "priority", "deadline", "parent", "start_date", "estimated_hours", "progress")


class TaskStatusUpdateSerializer(serializers.Serializer):
    status = serializers.SlugRelatedField(
        slug_field="code", queryset=TaskStatus.objects.all()
    )
    note = serializers.CharField(
        required=False, allow_blank=True, max_length=500, trim_whitespace=True
    )


class TaskChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskChecklistItem
        fields = ("id", "title", "is_completed", "position", "created_at")
        read_only_fields = ("id", "position", "created_at")


class TaskChecklistOrderSerializer(serializers.Serializer):
    item_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=True)


class TaskFilterSerializer(serializers.Serializer):
    project = serializers.IntegerField(required=False, min_value=1)
    assignee = serializers.IntegerField(required=False, min_value=1)
    status = serializers.ChoiceField(required=False, choices=TaskStatus.Code.choices)
    priority = serializers.ChoiceField(required=False, choices=Task.Priority.choices)
    deadline = serializers.DateField(required=False)
    deadline_from = serializers.DateField(required=False)
    deadline_to = serializers.DateField(required=False)
    overdue = serializers.BooleanField(required=False)
    due_soon = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if attrs.get("deadline_from") and attrs.get("deadline_to"):
            if attrs["deadline_from"] > attrs["deadline_to"]:
                raise serializers.ValidationError(
                    {"deadline_to": "Phải sau hoặc bằng ngày bắt đầu."}
                )
        if attrs.get("overdue") and attrs.get("due_soon"):
            raise serializers.ValidationError(
                "Không thể lọc đồng thời quá hạn và sắp hạn."
            )
        return attrs


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


class TaskAuditLogSerializer(serializers.ModelSerializer):
    actor = TaskUserSerializer(read_only=True)

    class Meta:
        model = TaskAuditLog
        fields = ("id", "actor", "action", "changes", "created_at")


class TaskAuditLogListDataSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    next = serializers.URLField(read_only=True, allow_null=True)
    previous = serializers.URLField(read_only=True, allow_null=True)
    results = TaskAuditLogSerializer(many=True, read_only=True)


class TaskAuditLogListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = TaskAuditLogListDataSerializer(read_only=True)

