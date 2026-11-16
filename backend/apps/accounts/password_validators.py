from django.core.exceptions import ValidationError


class NonWhitespacePasswordValidator:
    def validate(self, password, user=None):
        if not password.strip():
            raise ValidationError(self.get_help_text(), code="password_only_whitespace")

    def get_help_text(self):
        return "Mật khẩu không được chỉ chứa khoảng trắng."
