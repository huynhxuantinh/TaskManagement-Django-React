from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Q

from .models import Task, TaskStatus


def progress_task_queryset():
    return (
        Task.objects.filter(is_deleted=False, project__is_deleted=False)
        .select_related("status")
        .annotate(
            checklist_total_count=Count("checklist_items", distinct=True),
            checklist_done_count=Count(
                "checklist_items",
                filter=Q(checklist_items__is_completed=True),
                distinct=True,
            ),
        )
    )


def base_task_progress(task: Task) -> int:
    if task.status.code == TaskStatus.Code.COMPLETED:
        return 100
    if hasattr(task, "checklist_total_count"):
        total = task.checklist_total_count
        done = task.checklist_done_count
    else:
        checklist = list(task.checklist_items.all())
        total = len(checklist)
        done = sum(item.is_completed for item in checklist)
    return round(done * 100 / total) if total else task.progress


def weighted_task_summary(tasks: list[Task]) -> dict[str, int | Decimal]:
    if not tasks:
        return {"progress": 0, "estimated_hours": Decimal("0"), "missing_count": 0}
    estimates = [task.estimated_hours for task in tasks if task.estimated_hours is not None]
    default_weight = sum(estimates, Decimal("0")) / len(estimates) if estimates else Decimal("1")
    weights = [task.estimated_hours or default_weight for task in tasks]
    total_weight = sum(weights, Decimal("0"))
    contribution = sum(
        weight * Decimal(base_task_progress(task))
        for task, weight in zip(tasks, weights, strict=True)
    )
    return {
        "progress": round(contribution / total_weight) if total_weight else 0,
        "estimated_hours": total_weight,
        "missing_count": sum(task.estimated_hours is None for task in tasks),
    }


def task_progress_summary(task: Task) -> dict[str, int | Decimal | None]:
    cached = getattr(task, "_progress_summary_cache", None)
    if cached is not None:
        return cached
    children = getattr(task, "active_subtasks", None)
    if children is None:
        children = list(progress_task_queryset().filter(parent_id=task.id).order_by("id"))
    if children:
        summary = weighted_task_summary(children)
        if task.status.code == TaskStatus.Code.COMPLETED:
            summary["progress"] = 100
        task._progress_summary_cache = summary
        return summary
    summary = {
        "progress": base_task_progress(task),
        "estimated_hours": task.estimated_hours,
        "missing_count": int(task.estimated_hours is None),
    }
    task._progress_summary_cache = summary
    return summary


def project_progress_summaries(
    project_ids: list[int], tasks: list[Task] | None = None
) -> dict[int, dict[str, int | Decimal]]:
    if not project_ids:
        return {}
    rows = tasks
    if rows is None:
        rows = list(
            progress_task_queryset()
            .filter(project_id__in=project_ids)
            .order_by("project_id", "id")
        )
    children_by_parent: dict[int, list[Task]] = defaultdict(list)
    roots_by_project: dict[int, list[Task]] = defaultdict(list)
    for task in rows:
        if task.parent_id:
            children_by_parent[task.parent_id].append(task)
        else:
            roots_by_project[task.project_id].append(task)

    summaries = {}
    for project_id in project_ids:
        units = []
        for root in roots_by_project[project_id]:
            children = children_by_parent.get(root.id, [])
            units.extend(children or [root])
        summaries[project_id] = weighted_task_summary(units)
    return summaries
