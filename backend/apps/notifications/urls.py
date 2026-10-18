from django.urls import path

from .views import NotificationViewSet

notification_list = NotificationViewSet.as_view({"get": "list"})
notification_read = NotificationViewSet.as_view({"patch": "mark_read"})
notification_read_all = NotificationViewSet.as_view({"post": "read_all"})

urlpatterns = [
    path("notifications/", notification_list, name="notification-list"),
    path("notifications/read-all/", notification_read_all, name="notification-read-all"),
    path("notifications/<int:pk>/read/", notification_read, name="notification-read"),
]

