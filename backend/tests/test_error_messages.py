import pytest
from django.http import Http404
from rest_framework.exceptions import NotAuthenticated, NotFound, Throttled

from apps.core.api import exception_handler


@pytest.mark.parametrize(
    ("exception", "message"),
    [
        (Http404("No Task matches the given query."), "Không tìm thấy tài nguyên."),
        (NotFound(), "Không tìm thấy tài nguyên."),
        (NotFound("Không tìm thấy mục checklist."), "Không tìm thấy mục checklist."),
        (NotAuthenticated(), "Vui lòng đăng nhập để tiếp tục."),
        (Throttled(wait=60), "Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau 60 giây."),
    ],
)
def test_system_errors_are_localized_without_overwriting_specific_errors(exception, message):
    assert exception_handler(exception, {}).data["message"] == message
