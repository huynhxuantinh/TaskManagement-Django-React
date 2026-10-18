from rest_framework.permissions import BasePermission

from .models import Role


def has_role(user, *role_codes):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.role.code in role_codes
    )


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, Role.Code.ADMIN)


class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, Role.Code.ADMIN, Role.Code.MANAGER)


class IsSelfOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.pk == request.user.pk or has_role(request.user, Role.Code.ADMIN)
