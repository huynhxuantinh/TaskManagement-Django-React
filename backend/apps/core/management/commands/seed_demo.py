from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

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
            code: Role.objects.update_or_create(code=code, defaults={'name': label})[0]
            for code, label in Role.Code.choices
        }
        statuses = {
            code: TaskStatus.objects.update_or_create(
                code=code, defaults={'name': label}
            )[0]
            for code, label in TaskStatus.Code.choices
        }

        users = {}
        account_rows = (
            ('admin', 'admin', 'admin1@task.com', 'Quản trị viên', Role.Code.ADMIN),
            ('manager', 'qltask', 'manager1@task.com', 'Nguyễn Quản lý', Role.Code.MANAGER),
            ('employee', 'user', 'employee1@task.com', 'Trần Nhân viên', Role.Code.EMPLOYEE),
        )
        for key, username, email, full_name, role_code in account_rows:
            user, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    'username': username,
                    'full_name': full_name,
                    'role': roles[role_code],
                    'is_active': True,
                    'is_staff': role_code == Role.Code.ADMIN,
                },
            )
            user.set_password('123')
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
        gamma, _ = Project.objects.update_or_create(
            name='Ứng dụng quản lý nhân sự',
            creator=users['manager'],
            defaults={
                'description': 'Số hóa hồ sơ nhân viên và quy trình phê duyệt nội bộ.',
                'start_date': date(2026, 10, 15),
                'end_date': date(2027, 2, 28),
                'is_deleted': False,
            },
        )
        delta, _ = Project.objects.update_or_create(
            name='Tự động hóa kiểm thử',
            creator=users['admin'],
            defaults={
                'description': 'Xây dựng bộ kiểm thử tự động cho các luồng nghiệp vụ chính.',
                'start_date': date(2026, 10, 18),
                'end_date': date(2026, 12, 31),
                'is_deleted': False,
            },
        )
        for project, members in (
            (alpha, (users['admin'], users['manager'], users['employee'])),
            (beta, (users['admin'], users['employee'])),
            (gamma, (users['manager'], users['employee'])),
            (delta, (users['admin'], users['manager'], users['employee'])),
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
            (gamma, 'Phân tích quy trình nhân sự', users['manager'], 'COMPLETED', 2, date(2026, 10, 22)),
            (gamma, 'Thiết kế màn hình hồ sơ', users['employee'], 'IN_PROGRESS', 2, date(2026, 11, 12)),
            (gamma, 'Xây dựng luồng phê duyệt', users['employee'], 'TODO', 3, date(2026, 11, 30)),
            (delta, 'Viết kiểm thử API', users['admin'], 'IN_PROGRESS', 3, date(2026, 11, 5)),
            (delta, 'Viết kiểm thử giao diện', users['employee'], 'TODO', 2, date(2026, 11, 15)),
            (delta, 'Tích hợp kiểm thử vào CI', users['manager'], 'ON_HOLD', 2, date(2026, 12, 5)),
        )
        for project, title, assignee, status_code, priority, deadline in task_rows:
            completed_at = (
                timezone.make_aware(
                    datetime.combine(deadline - timedelta(days=1), time(hour=16))
                )
                if status_code == TaskStatus.Code.COMPLETED
                else None
            )
            Task.objects.update_or_create(
                project=project,
                title=title,
                defaults={
                    'description': f'Dữ liệu mẫu cho {title.lower()}.',
                    'assignee': assignee,
                    'status': statuses[status_code],
                    'priority': priority,
                    'deadline': deadline,
                    'completed_at': completed_at,
                    'is_deleted': False,
                },
            )

        notification_rows = (
            (users['employee'], 'Bạn được giao công việc Xây dựng giao diện công việc.', NotificationType.TASK_ASSIGNED, True),
            (users['manager'], 'Tiến độ dự án vừa được cập nhật.', NotificationType.STATUS_CHANGED, False),
        )
        Notification.objects.filter(
            user=users['employee'],
            message='Công việc "Kiểm thử phân quyền" sắp đến hạn.',
            type=NotificationType.DEADLINE_APPROACHING,
        ).delete()
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
                    defaults={
                        'is_priority': notification_type in (
                            NotificationType.DEADLINE_APPROACHING,
                            NotificationType.DEADLINE_OVERDUE,
                        )
                    },
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
        self.stdout.write(self.style.SUCCESS('Dữ liệu mẫu đã sẵn sàng.'))
