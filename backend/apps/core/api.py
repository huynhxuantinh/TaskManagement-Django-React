from django.middleware.csrf import CsrfViewMiddleware
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def success(data=None, message="Thành công.", status=200):
    return Response(
        {"success": True, "message": message, "data": data}, status=status
    )


def failure(message, errors=None, status=400):
    return Response(
        {
            "success": False,
            "message": message,
            "data": None,
            "errors": errors or {},
        },
        status=status,
    )


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    detail = response.data
    if isinstance(detail, dict) and set(detail) == {"detail"}:
        message = str(detail["detail"])
        errors = {}
    else:
        message = "Dữ liệu không hợp lệ."
        errors = detail
    response.data = {
        "success": False,
        "message": message,
        "data": None,
        "errors": errors,
    }
    return response


def enforce_csrf(request):
    reason = CsrfViewMiddleware(lambda _request: None).process_view(
        request._request, None, (), {}
    )
    if reason:
        raise PermissionDenied("CSRF verification failed.")
