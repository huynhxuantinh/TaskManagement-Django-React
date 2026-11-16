from django.db import IntegrityError, transaction

from apps.notifications.models import NotificationType
from apps.notifications.services import create_notification

from .models import Project, ProjectMember


class MembershipConflict(Exception):
    pass


class CreatorRemovalConflict(Exception):
    pass


class AssignedTasksConflict(Exception):
    pass


class ProjectService:
    @staticmethod
    @transaction.atomic
    def create_project(creator, validated_data, actor=None):
        project = Project.objects.create(creator=creator, **validated_data)
        ProjectMember.objects.create(project=project, user=creator)
        if actor is not None and actor.pk != creator.pk:
            create_notification(
                creator, NotificationType.PROJECT_ADDED,
                f'Bạn được chỉ định làm chủ dự án "{project.name}".',
            )
        return project

    @staticmethod
    @transaction.atomic
    def add_member(project, user):
        try:
            membership, created = ProjectMember.objects.get_or_create(
                project=project, user=user
            )
        except IntegrityError as error:
            raise MembershipConflict from error
        if not created:
            raise MembershipConflict
        create_notification(
            user,
            NotificationType.PROJECT_ADDED,
            f'Bạn đã được thêm vào dự án "{project.name}".',
        )
        return membership

    @staticmethod
    @transaction.atomic
    def remove_member(project, user_id):
        from apps.tasks.models import Task, TaskStatus

        if project.creator_id == user_id:
            raise CreatorRemovalConflict
        membership = ProjectMember.objects.select_for_update(of=('self',)).filter(
            project=project, user_id=user_id
        ).first()
        if membership is None:
            return False
        if Task.objects.filter(
            project=project,
            assignee_id=user_id,
            is_deleted=False,
        ).exclude(status__code=TaskStatus.Code.COMPLETED).exists():
            raise AssignedTasksConflict
        removed_user = membership.user
        membership.delete()
        create_notification(
            removed_user, NotificationType.GENERAL,
            f'Bạn đã được xóa khỏi dự án "{project.name}".',
        )
        return True
