import pytest
from django.core.management import call_command

from apps.accounts.models import Role, User
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectMember
from apps.reports.models import ReportMessage
from apps.tasks.models import Task, TaskStatus


@pytest.mark.django_db
def test_seed_demo_creates_stable_idempotent_e2e_dataset():
    call_command('seed_demo')

    assert set(Role.objects.values_list('code', flat=True)) == set(Role.Code.values)
    assert set(TaskStatus.objects.values_list('code', flat=True)) == set(TaskStatus.Code.values)
    assert User.objects.get(email='admin1@task.com').check_password('Admin@123')
    assert User.objects.get(email='manager1@task.com').check_password('Manager@123')
    assert User.objects.get(email='employee1@task.com').check_password('Employee@123')
    assert Project.objects.filter(is_deleted=False).count() == 2
    assert ProjectMember.objects.count() == 5
    assert Task.objects.filter(is_deleted=False).count() == 6
    assert Notification.objects.count() >= 3
    assert ReportMessage.objects.count() == 1

    counts = {
        'users': User.objects.count(),
        'projects': Project.objects.count(),
        'members': ProjectMember.objects.count(),
        'tasks': Task.objects.count(),
        'notifications': Notification.objects.count(),
        'reports': ReportMessage.objects.count(),
    }
    call_command('seed_demo')
    assert counts == {
        'users': User.objects.count(),
        'projects': Project.objects.count(),
        'members': ProjectMember.objects.count(),
        'tasks': Task.objects.count(),
        'notifications': Notification.objects.count(),
        'reports': ReportMessage.objects.count(),
    }
