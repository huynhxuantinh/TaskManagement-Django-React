from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class Role(models.Model):
    class Code(models.TextChoices):
        ADMIN = "ADMIN", "Quản trị viên"
        MANAGER = "MANAGER", "Quản lý"
        EMPLOYEE = "EMPLOYEE", "Nhân viên"

    legacy_id = models.PositiveBigIntegerField(unique=True)
    code = models.CharField(max_length=20, choices=Code.choices, unique=True)
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email là bắt buộc")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Quản trị viên cấp cao phải có is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Quản trị viên cấp cao phải có is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=100, unique=True)
    username = models.CharField(max_length=50, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="users")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    avatar = models.CharField(max_length=500, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_uniq"),
            models.UniqueConstraint(
                Lower("username"), name="accounts_user_username_ci_uniq"
            ),
        ]
        indexes = [models.Index(fields=["role", "is_active"], name="user_role_active_idx")]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        if self.username:
            self.username = self.username.strip().lower()
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split(maxsplit=1)[0]

    def __str__(self):
        return self.email
