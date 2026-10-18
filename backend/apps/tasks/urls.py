from django.urls import path

from .views import TaskStatusListView, TaskViewSet

task_list = TaskViewSet.as_view({"get": "list", "post": "create"})
task_detail = TaskViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
task_status = TaskViewSet.as_view({"patch": "change_status"})

urlpatterns = [
    path("metadata/task-statuses/", TaskStatusListView.as_view(), name="task-statuses"),
    path("tasks/", task_list, name="task-list"),
    path("tasks/<int:pk>/", task_detail, name="task-detail"),
    path("tasks/<int:pk>/status/", task_status, name="task-change-status"),
]

