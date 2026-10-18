from django.urls import path

from .views import ProjectViewSet

project_list = ProjectViewSet.as_view({"get": "list", "post": "create"})
project_detail = ProjectViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
project_members = ProjectViewSet.as_view({"get": "members", "post": "members"})
project_member_detail = ProjectViewSet.as_view({"delete": "remove_member"})

urlpatterns = [
    path("projects/", project_list, name="project-list"),
    path("projects/<int:pk>/", project_detail, name="project-detail"),
    path("projects/<int:pk>/members/", project_members, name="project-members"),
    path(
        "projects/<int:pk>/members/<int:user_id>/",
        project_member_detail,
        name="project-member-detail",
    ),
]
