from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet

from apps.core.api import success
from apps.core.pagination import StandardPagination

from .models import Notification, NotificationType
from .serializers import (
    NotificationListResponseSerializer,
    NotificationResponseSerializer,
    NotificationSerializer,
    ReadAllResponseSerializer,
)


class NotificationViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user).order_by(
            "-created_at", "-id"
        )
        is_read = self.request.query_params.get("is_read")
        if is_read in {"true", "false"}:
            queryset = queryset.filter(is_read=is_read == "true")
        notification_type = self.request.query_params.get("type")
        if notification_type in NotificationType.values:
            queryset = queryset.filter(type=notification_type)
        return queryset

    @extend_schema(tags=["Notifications"], responses={200: NotificationListResponseSerializer})
    def list(self, request):
        paginator = StandardPagination()
        page = paginator.paginate_queryset(self.get_queryset(), request, view=self)
        return paginator.get_paginated_response(
            NotificationSerializer(page, many=True).data
        )

    @extend_schema(tags=["Notifications"], request=None, responses={200: NotificationResponseSerializer})
    def mark_read(self, request, pk=None):
        notification = get_object_or_404(self.get_queryset(), pk=pk)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return success(
            NotificationSerializer(notification).data,
            "Đánh dấu thông báo đã đọc thành công.",
        )

    @extend_schema(tags=["Notifications"], request=None, responses={200: ReadAllResponseSerializer})
    def read_all(self, request):
        updated_count = self.get_queryset().filter(is_read=False).update(is_read=True)
        return success(
            {"updated_count": updated_count},
            "Đánh dấu tất cả thông báo đã đọc thành công.",
        )

