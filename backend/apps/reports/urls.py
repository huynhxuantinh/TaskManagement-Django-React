from django.urls import path

from .views import (
    DashboardSummaryView,
    ProjectReportView,
    ReportMessageListCreateView,
    ReportMessageReadView,
    TopContributorsView,
    WorkloadView,
)

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("reports/workload/", WorkloadView.as_view(), name="report-workload"),
    path(
        "reports/projects/<int:project_id>/",
        ProjectReportView.as_view(),
        name="project-report",
    ),
    path(
        "reports/projects/<int:project_id>/top-contributors/",
        TopContributorsView.as_view(),
        name="project-top-contributors",
    ),
    path(
        "reports/messages/",
        ReportMessageListCreateView.as_view(),
        name="report-message-list",
    ),
    path(
        "reports/messages/<int:pk>/read/",
        ReportMessageReadView.as_view(),
        name="report-message-read",
    ),
]
