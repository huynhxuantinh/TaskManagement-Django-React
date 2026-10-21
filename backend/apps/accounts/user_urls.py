from django.urls import path
from rest_framework.parsers import FormParser, MultiPartParser

from .user_views import UserViewSet

user_list = UserViewSet.as_view({"get": "list", "post": "create"})
user_detail = UserViewSet.as_view({"get": "retrieve", "patch": "partial_update"})
user_role = UserViewSet.as_view({"patch": "change_role"})
user_avatar = UserViewSet.as_view(
    {"post": "upload_avatar"}, parser_classes=[MultiPartParser, FormParser]
)
user_preferences = UserViewSet.as_view({"get": "preferences", "put": "preferences"})

urlpatterns = [
    path("users/", user_list, name="user-list"),
    path("users/<int:pk>/", user_detail, name="user-detail"),
    path("users/<int:pk>/role/", user_role, name="user-role"),
    path("users/<int:pk>/avatar/", user_avatar, name="user-avatar"),
    path("users/<int:pk>/preferences/", user_preferences, name="user-preferences"),
]
