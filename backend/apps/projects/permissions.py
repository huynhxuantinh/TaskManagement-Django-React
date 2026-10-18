from apps.accounts.models import Role
from apps.accounts.permissions import has_role


def can_create_project(user):
    return has_role(user, Role.Code.ADMIN, Role.Code.MANAGER)


def can_manage_project(user, project):
    return has_role(user, Role.Code.ADMIN) or (
        has_role(user, Role.Code.MANAGER) and project.creator_id == user.id
    )
