import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

from apps.accounts.models import Role, User


class Command(BaseCommand):
    help = "Create the first production administrator from BOOTSTRAP_ADMIN_* variables."

    @transaction.atomic
    def handle(self, *args, **options):
        email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
        full_name = os.getenv("BOOTSTRAP_ADMIN_FULL_NAME", "").strip()
        username = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "").strip().lower() or None
        password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")

        if not email:
            raise CommandError("BOOTSTRAP_ADMIN_EMAIL là bắt buộc.")
        if not full_name:
            raise CommandError("BOOTSTRAP_ADMIN_FULL_NAME là bắt buộc.")
        if not password:
            raise CommandError("BOOTSTRAP_ADMIN_PASSWORD là bắt buộc.")
        try:
            validate_email(email)
        except ValidationError as error:
            raise CommandError("BOOTSTRAP_ADMIN_EMAIL không hợp lệ.") from error

        role = Role.objects.filter(code=Role.Code.ADMIN).first()
        if role is None:
            raise CommandError("Thiếu vai trò ADMIN. Hãy chạy migrate trước.")

        existing = User.objects.select_related("role").filter(email__iexact=email).first()
        if existing is not None:
            if existing.is_superuser and existing.role_id == role.id:
                self.stdout.write(self.style.SUCCESS("Tài khoản quản trị đã tồn tại; không thay đổi mật khẩu."))
                return
            raise CommandError("Email bootstrap đã thuộc một tài khoản không phải quản trị viên cấp cao.")

        candidate = User(
            email=email,
            username=username,
            full_name=full_name,
            role=role,
            is_staff=True,
            is_superuser=True,
        )
        try:
            validate_password(password, candidate)
        except ValidationError as error:
            raise CommandError("Mật khẩu bootstrap không đạt yêu cầu: " + " ".join(error.messages)) from error

        try:
            User.objects.create_superuser(
                email=email,
                username=username,
                full_name=full_name,
                password=password,
                role=role,
            )
        except IntegrityError as error:
            raise CommandError("Email hoặc tên đăng nhập bootstrap đã tồn tại.") from error
        self.stdout.write(self.style.SUCCESS("Đã tạo tài khoản quản trị production."))
