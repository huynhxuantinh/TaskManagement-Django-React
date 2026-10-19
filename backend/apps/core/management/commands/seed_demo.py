from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Role, User
from apps.notifications.models import Notification, NotificationType, Preference
from apps.projects.models import Project, ProjectMember
from apps.reports.models import ReportMessage
from apps.tasks.models import Task, TaskStatus


class Command(BaseCommand):
    help = 'Create the deterministic demo dataset used by local and E2E environments.'

    @transaction.atomic
    def handle(self, *args, **options):
        roles = {
            code: Role.objects.update_or_create(
                code=code,
                defaults={'name': label, 'legacy_id': index},
            )[0]
            for index, (code, label) in enumerate(Role.Code.choices, start=1)
        }
        statuses = {
            code: TaskStatus.objects.update_or_create(
                code=code,
                defaults={'name': label, 'legacy_id': index},
            )[0]
            for index, (code, label) in enumerate(TaskStatus.Code.choices, start=1)
        }

        users = {}
        account_rows = (
            ('admin', 'admin1@task.com', 'Quản trị viên', Role.Code.ADMIN, 'Admin@123'),
            ('manager', 'manager1@task.com', 'Nguyễn Quản lý', Role.Code.MANAGER, 'Manager@123'),
            ('employee', 'employee1@task.com', 'Trần Nhân viên', Role.Code.EMPLOYEE, 'Employee@123'),
        )
        for key, email, full_name, role_code, password in account_rows:
            user, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    'full_name': full_name,
                    'role': roles[role_code],
                    'is_active': True,
                    'is_staff': role_code == Role.Code.ADMIN,
                },
            )
            user.set_password(password)
            user.save(update_fields=['password'])
            users[key] = user

        alpha, _ = Project.objects.update_or_create(
            name='Nền tảng quản lý nội bộ',
            creator=users['manager'],
            defaults={
                'description': 'Chuẩn hóa quy trình giao việc và theo dõi tiến độ.',
                'start_date': date(2026, 10, 1),
                'end_date': date(2026, 12, 20),
                'is_deleted': False,
            },
        )
        beta, _ = Project.objects.update_or_create(
            name='Cổng báo cáo vận hành',
            creator=users['admin'],
            defaults={
                'description': 'Tổng hợp tín hiệu dự án cho quản lý.',
                'start_date': date(2026, 10, 10),
                'end_date': date(2027, 1, 15),
                'is_deleted': False,
            },
        )
        for project, members in (
            (alpha, (users['admin'], users['manager'], users['employee'])),
            (beta, (users['admin'], users['employee'])),
        ):
            for user in members:
                ProjectMember.objects.get_or_create(project=project, user=user)

        task_rows = (
            (alpha, 'Thiết kế API dự án', users['manager'], 'COMPLETED', 2, date(2026, 10, 12)),
            (alpha, 'Xây dựng giao diện công việc', users['employee'], 'IN_PROGRESS', 3, date(2026, 10, 28)),
            (alpha, 'Kiểm thử phân quyền', users['employee'], 'TODO', 3, date(2026, 11, 3)),
            (beta, 'Chốt chỉ số dashboard', users['admin'], 'COMPLETED', 2, date(2026, 10, 16)),
            (beta, 'Tích hợp báo cáo dự án', users['employee'], 'IN_PROGRESS', 2, date(2026, 11, 8)),
            (beta, 'Viết runbook triển khai', users['admin'], 'TODO', 1, date(2026, 11, 20)),
        )
        for project, title, assignee, status_code, priority, deadline in task_rows:
            Task.objects.update_or_create(
                project=project,
                title=title,
                defaults={
                    'description': f'Dữ liệu mẫu cho {title.lower()}.',
                    'assignee': assignee,
                    'status': statuses[status_code],
                    'priority': priority,
                    'deadline': deadline,
                    'is_deleted': False,
                },
            )

        notification_rows = (
            (users['employee'], 'Bạn được giao công việc Xây dựng giao diện công việc.', NotificationType.TASK_ASSIGNED, True),
            (users['employee'], 'Deadline Kiểm thử phân quyền đang đến gần.', NotificationType.DEADLINE_APPROACHING, True),
            (users['manager'], 'Tiến độ dự án vừa được cập nhật.', NotificationType.STATUS_CHANGED, False),
        )
        for user, message, notification_type, priority in notification_rows:
            Notification.objects.update_or_create(
                user=user,
                message=message,
                defaults={'type': notification_type, 'is_priority': priority},
            )
        for user in users.values():
            for notification_type in NotificationType.values:
                Preference.objects.get_or_create(
                    user=user,
                    type=notification_type,
                    defaults={'is_priority': notification_type == NotificationType.DEADLINE_APPROACHING},
                )

        ReportMessage.objects.update_or_create(
            project=alpha,
            sender=users['manager'],
            receiver=users['admin'],
            title='Báo cáo tiến độ tuần',
            defaults={
                'content': 'API dự án đã hoàn thành, giao diện công việc đang đúng tiến độ.',
                'is_read': False,
            },
        )
        self.stdout.write(self.style.SUCCESS('Demo data is ready.'))
