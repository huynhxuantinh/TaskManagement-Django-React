from django.urls import path

from .views import TaskAssigneeListView, TaskChecklistItemView, TaskChecklistOrderView, TaskChecklistView, TaskStatusListView, TaskViewSet

task_list = TaskViewSet.as_view({"get": "list", "post": "create"})
task_detail = TaskViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
task_status = TaskViewSet.as_view({"patch": "change_status"})
task_history = TaskViewSet.as_view({"get": "history"})
task_export = TaskViewSet.as_view({"get": "export"})

urlpatterns = [
    path("metadata/task-statuses/", TaskStatusListView.as_view(), name="task-statuses"),
    path("metadata/task-assignees/", TaskAssigneeListView.as_view(), name="task-assignees"),
    path("tasks/", task_list, name="task-list"),
    path("tasks/export/", task_export, name="task-export"),
    path("tasks/<int:pk>/", task_detail, name="task-detail"),
    path("tasks/<int:pk>/status/", task_status, name="task-change-status"),
    path("tasks/<int:pk>/history/", task_history, name="task-history"),
    path("tasks/<int:pk>/checklist/", TaskChecklistView.as_view(), name="task-checklist"),
    path("tasks/<int:pk>/checklist/order/", TaskChecklistOrderView.as_view(), name="task-checklist-order"),
    path("tasks/<int:pk>/checklist/<int:item_id>/", TaskChecklistItemView.as_view(), name="task-checklist-item"),
]

