from django.db.models import Count, F, Prefetch, Q
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.accounts.permissions import has_role
from apps.projects.models import Project
from apps.tasks.models import Task, TaskStatus
from apps.tasks.progress import progress_task_queryset, project_progress_summaries


def scoped_projects(user):
    queryset = Project.objects.filter(is_deleted=False)
    if has_role(user, Role.Code.ADMIN):
        return queryset
    return queryset.filter(memberships__user=user).distinct()


def scoped_tasks(user):
    queryset = Task.objects.filter(
        is_deleted=False, project__is_deleted=False
    ).select_related("project", "assignee", "assignee__role", "status")
    if has_role(user, Role.Code.ADMIN):
        return queryset
    if has_role(user, Role.Code.MANAGER):
        return queryset.filter(project__memberships__user=user).distinct()
    return queryset.filter(
        assignee=user,
        project__memberships__user=user,
    ).distinct()


def dashboard_summary(user):
    projects = scoped_projects(user)
    tasks = scoped_tasks(user)
    today = timezone.localdate()
    totals = tasks.aggregate(
        task_count=Count("id"),
        completed_task_count=Count(
            "id", filter=Q(status__code=TaskStatus.Code.COMPLETED)
        ),
        overdue_task_count=Count(
            "id",
            filter=Q(deadline__lt=today) & ~Q(status__code=TaskStatus.Code.COMPLETED),
        ),
        missing_estimate_count=Count(
            "id", filter=Q(estimated_hours__isnull=True)
        ),
    )
    distribution = list(
        tasks.values("status__code", "status__name")
        .annotate(count=Count("id"))
        .order_by("status__code")
    )
    if has_role(user, Role.Code.ADMIN):
        team_count = User.objects.filter(is_active=True).count()
    else:
        team_count = (
            User.objects.filter(is_active=True, project_memberships__project__in=projects)
            .distinct()
            .count()
        )
    return {
        "project_count": projects.count(),
        **totals,
        "team_count": team_count,
        "task_distribution": [
            {"code": row["status__code"], "name": row["status__name"], "count": row["count"]}
            for row in distribution
        ],
        "recent_tasks": list(
            tasks.annotate(
                checklist_total_count=Count("checklist_items", distinct=True),
                checklist_done_count=Count(
                    "checklist_items",
                    filter=Q(checklist_items__is_completed=True),
                    distinct=True,
                ),
            )
            .prefetch_related(
                "checklist_items",
                Prefetch(
                    "subtasks",
                    queryset=progress_task_queryset().order_by("id"),
                    to_attr="active_subtasks",
                ),
            )
            .order_by("-created_at", "-id")[:5]
        ),
    }


def workload(user):
    users = User.objects.filter(is_active=True, role__code=Role.Code.EMPLOYEE)
    task_filter = Q(
        assigned_tasks__is_deleted=False,
        assigned_tasks__project__is_deleted=False,
    )
    if has_role(user, Role.Code.MANAGER):
        users = users.filter(
            project_memberships__project__memberships__user=user,
            project_memberships__project__is_deleted=False,
        ).distinct()
        task_filter &= Q(assigned_tasks__project__memberships__user=user)
    completed_filter = task_filter & Q(
        assigned_tasks__status__code=TaskStatus.Code.COMPLETED
    )
    before_deadline_filter = completed_filter & Q(
        assigned_tasks__deadline__isnull=False,
        assigned_tasks__completed_at__isnull=False,
        assigned_tasks__completed_at__date__lte=F("assigned_tasks__deadline"),
    )
    return users.select_related("role").annotate(
        total_tasks=Count("assigned_tasks", filter=task_filter, distinct=True),
        active_tasks=Count(
            "assigned_tasks",
            filter=task_filter
            & ~Q(assigned_tasks__status__code=TaskStatus.Code.COMPLETED),
            distinct=True,
        ),
        completed_before_deadline=Count(
            "assigned_tasks", filter=before_deadline_filter, distinct=True
        ),
    )


def project_report(project):
    tasks = list(progress_task_queryset().filter(project=project).order_by("id"))
    progress = project_progress_summaries([project.id], tasks)[project.id]
    distribution = {}
    for task in tasks:
        row = distribution.setdefault(
            task.status.code,
            {"code": task.status.code, "name": task.status.name, "count": 0},
        )
        row["count"] += 1
    return {
        "project_id": project.id,
        "project_name": project.name,
        "total_tasks": len(tasks),
        "completed_tasks": sum(
            task.status.code == TaskStatus.Code.COMPLETED for task in tasks
        ),
        "progress": progress["progress"],
        "missing_estimate_count": progress["missing_count"],
        "task_distribution": [distribution[code] for code in sorted(distribution)],
    }


def top_contributors(project):
    return list(
        Task.objects.filter(
            project=project, is_deleted=False, assignee__isnull=False
        )
        .values(
            user_id=F("assignee_id"),
            full_name=F("assignee__full_name"),
            email=F("assignee__email"),
        )
        .annotate(
            completed_tasks=Count(
                "id", filter=Q(status__code=TaskStatus.Code.COMPLETED)
            ),
            total_tasks=Count("id"),
        )
        .order_by("-completed_tasks", "-total_tasks", "full_name")
    )

