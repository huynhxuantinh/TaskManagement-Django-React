from rest_framework import serializers

from apps.accounts.models import User

from .models import Project, ProjectMember


class ProjectUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.code", read_only=True)
    avatar_url = serializers.CharField(source="avatar", read_only=True)

    class Meta:
        model = User
        fields = ("id", "full_name", "email", "role", "avatar_url")


class ProjectSerializer(serializers.ModelSerializer):
    creator = ProjectUserSerializer(read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    progress = serializers.SerializerMethodField()
    missing_estimate_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "description",
            "start_date",
            "end_date",
            "creator",
            "member_count",
            "progress",
            "missing_estimate_count",
            "created_at",
        )

    def get_progress(self, project) -> int:
        return getattr(project, "weighted_progress", 0)


class ProjectWriteSerializer(serializers.ModelSerializer):
    creator_id = serializers.PrimaryKeyRelatedField(
        source="creator",
        queryset=User.objects.filter(
            is_active=True, role__code="MANAGER"
        ),
        required=False,
    )

    class Meta:
        model = Project
        fields = ("name", "description", "start_date", "end_date", "creator_id")

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": ["Ngày kết thúc phải từ ngày bắt đầu trở đi."]}
            )
        return attrs


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = ProjectUserSerializer(read_only=True)

    class Meta:
        model = ProjectMember
        fields = ("id", "user", "joined_at")


class AddMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False, min_value=1)
    email = serializers.EmailField(required=False, max_length=100)

    def validate(self, attrs):
        if ("user_id" in attrs) == ("email" in attrs):
            raise serializers.ValidationError(
                "Chỉ cung cấp một trong user_id hoặc email."
            )
        if "email" in attrs:
            attrs["email"] = attrs["email"].strip().lower()
        return attrs


class ProjectResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = ProjectSerializer(read_only=True)


class ProjectListDataSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    next = serializers.URLField(read_only=True, allow_null=True)
    previous = serializers.URLField(read_only=True, allow_null=True)
    results = ProjectSerializer(many=True, read_only=True)


class ProjectListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = ProjectListDataSerializer(read_only=True)


class MemberResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = ProjectMemberSerializer(read_only=True)


class MemberListDataSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    next = serializers.URLField(read_only=True, allow_null=True)
    previous = serializers.URLField(read_only=True, allow_null=True)
    results = ProjectMemberSerializer(many=True, read_only=True)


class MemberListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = MemberListDataSerializer(read_only=True)
