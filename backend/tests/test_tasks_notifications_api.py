import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from io import StringIO
from threading import Event

import pytest
from django.db import close_old_connections, connections
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.notifications.models import Notification, NotificationType
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task, TaskAuditLog, TaskChecklistItem, TaskStatus
from apps.tasks.services import ChecklistService, TaskService


@pytest.fixture
def task_roles(db):
    return {
        code: Role.objects.get_or_create(code=code, defaults={"name": label})[0]
        for code, label in Role.Code.choices
    }


@pytest.fixture
def task_users(task_roles):
    def make(email, role):
        return User.objects.create_user(
            email=email,
            full_name=email.split("@")[0].title(),
            password="StrongPass@123",
            role=task_roles[role],
        )

    return {
        "admin": make("admin@example.com", Role.Code.ADMIN),
        "manager": make("manager@example.com", Role.Code.MANAGER),
        "manager2": make("manager2@example.com", Role.Code.MANAGER),
        "employee": make("employee@example.com", Role.Code.EMPLOYEE),
        "employee2": make("employee2@example.com", Role.Code.EMPLOYEE),
        "outsider": make("outsider@example.com", Role.Code.EMPLOYEE),
    }


@pytest.fixture
def task_statuses(db):
    return {
        code: TaskStatus.objects.get_or_create(code=code, defaults={"name": label})[0]
        for code, label in TaskStatus.Code.choices
    }


@pytest.fixture
def task_project(task_users):
    project = Project.objects.create(name="Internal ERP", creator=task_users["manager"])
    for user in (
        task_users["manager"],
        task_users["manager2"],
        task_users["employee"],
        task_users["employee2"],
    ):
        ProjectMember.objects.create(project=project, user=user)
    return project


def api_as(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user=user)
    return client


def make_task(project, statuses, assignee, **overrides):
    values = {
        "title": "Implement API",
        "description": "Task API contract",
        "project": project,
        "assignee": assignee,
        "status": statuses[TaskStatus.Code.TODO],
        "priority": Task.Priority.MEDIUM,
        "deadline": timezone.localdate() + timedelta(days=3),
    }
    values.update(overrides)
    return Task.objects.create(**values)


@pytest.mark.django_db
def test_task_create_enforces_role_membership_and_only_notifies_assignment(
    task_users, task_statuses, task_project
):
    payload = {
        "title": "Build task screen",
        "description": "React integration",
        "project_id": task_project.id,
        "assignee_id": task_users["employee"].id,
        "status": TaskStatus.Code.TODO,
        "priority": Task.Priority.HIGH,
        "deadline": "2026-10-25",
    }

    assert api_as().post("/api/v1/tasks/", payload, format="json").status_code == 401
    assert (
        api_as(task_users["employee"])
        .post("/api/v1/tasks/", payload, format="json")
        .status_code
        == 403
    )
    invalid = api_as(task_users["manager"]).post(
        "/api/v1/tasks/",
        {**payload, "assignee_id": task_users["outsider"].id},
        format="json",
    )
    created = api_as(task_users["manager"]).post(
        "/api/v1/tasks/", payload, format="json"
    )

    assert invalid.status_code == 400
    assert "assignee_id" in invalid.data["errors"]
    assert created.status_code == 201
    assert created.data["data"]["status"]["code"] == TaskStatus.Code.TODO
    assert created.data["data"]["assignee"]["id"] == task_users["employee"].id
    assert created.data["data"]["updated_at"] is not None
    creation_log = TaskAuditLog.objects.get(task_id=created.data["data"]["id"])
    assert creation_log.action == TaskAuditLog.Action.CREATED
    assert creation_log.actor == task_users["manager"]
    assert Notification.objects.filter(
        user=task_users["employee"], type=NotificationType.TASK_ASSIGNED
    ).exists()
    assert set(
        Notification.objects.filter(user=task_users["employee"]).values_list(
            "message", flat=True
        )
    ) == {
        'Bạn được giao công việc "Build task screen".',
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('action', ['create', 'update', 'delete', 'reorder'])
def test_checklist_write_rechecks_permission_after_concurrent_reassignment(task_users, task_statuses, task_project, monkeypatch, action):
    task = make_task(task_project, task_statuses, task_users['employee'])
    first = TaskChecklistItem.objects.create(task=task, title='First', position=0)
    second = TaskChecklistItem.objects.create(task=task, title='Second', position=1)
    passed_view = Event()
    proceed = Event()
    original = ChecklistService.locked_task

    def delayed_lock(*args, **kwargs):
        passed_view.set()
        assert proceed.wait(10)
        return original(*args, **kwargs)

    monkeypatch.setattr(ChecklistService, 'locked_task', delayed_lock)

    def write_checklist():
        close_old_connections()
        try:
            client = api_as(task_users['employee'])
            base = f'/api/v1/tasks/{task.id}/checklist/'
            if action == 'create':
                response = client.post(base, {'title': 'New'}, format='json')
            elif action == 'update':
                response = client.patch(f'{base}{first.id}/', {'title': 'Changed'}, format='json')
            elif action == 'delete':
                response = client.delete(f'{base}{first.id}/')
            else:
                response = client.put(f'{base}order/', {'item_ids': [second.id, first.id]}, format='json')
            return response.status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(write_checklist)
        try:
            assert passed_view.wait(10)
            reassigned = api_as(task_users['manager']).patch(f'/api/v1/tasks/{task.id}/', {
                'assignee_id': task_users['employee2'].id, 'expected_updated_at': task.updated_at.isoformat(),
            }, format='json')
            assert reassigned.status_code == 200
        finally:
            proceed.set()
        assert future.result(timeout=10) == 403
    assert list(task.checklist_items.order_by('position').values_list('title', flat=True)) == ['First', 'Second']
    assert not TaskAuditLog.objects.filter(task=task, action__startswith='CHECKLIST_').exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_parent_completion_and_child_reopening_remain_consistent(task_users, task_statuses, task_project, monkeypatch):
    parent = make_task(task_project, task_statuses, task_users['employee'], status=task_statuses['IN_PROGRESS'])
    child = make_task(task_project, task_statuses, task_users['employee'], parent=parent, status=task_statuses['COMPLETED'])
    child_at_validation = Event()
    parent_at_validation = Event()
    release_child = Event()
    from apps.tasks import services
    original = services.validate_transition

    def coordinated_validation(task, new_status, actor, note):
        if task.id == child.id:
            child_at_validation.set()
            assert release_child.wait(10)
        elif task.id == parent.id:
            parent_at_validation.set()
        return original(task, new_status, actor, note)

    monkeypatch.setattr(services, 'validate_transition', coordinated_validation)

    def change(is_parent):
        close_old_connections()
        try:
            target = parent if is_parent else child
            return api_as(task_users['manager']).patch(f'/api/v1/tasks/{target.id}/status/', {
                'status': 'COMPLETED' if is_parent else 'IN_PROGRESS',
                'expected_status': 'IN_PROGRESS' if is_parent else 'COMPLETED',
                'note': '' if is_parent else 'Mở lại',
            }, format='json').status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        reopening = executor.submit(change, False)
        try:
            assert child_at_validation.wait(10)
            completing = executor.submit(change, True)
            parent_at_validation.wait(1)
        finally:
            release_child.set()
        reopened = reopening.result(timeout=10)
        completed = completing.result(timeout=10)
    parent.refresh_from_db()
    child.refresh_from_db()
    assert not (parent.status.code == 'COMPLETED' and child.status.code != 'COMPLETED')
    assert (reopened, completed) in {(200, 400), (400, 200)}


@pytest.mark.django_db(transaction=True)
def test_status_change_rechecks_authorization_after_concurrent_reassignment(task_users, task_statuses, task_project, monkeypatch):
    task = make_task(task_project, task_statuses, task_users['employee'])
    authorized = Event()
    proceed = Event()
    original = TaskService.change_status

    def delayed_change(*args, **kwargs):
        authorized.set()
        assert proceed.wait(10)
        return original(*args, **kwargs)

    monkeypatch.setattr(TaskService, 'change_status', delayed_change)

    def change():
        close_old_connections()
        try:
            return api_as(task_users['employee']).patch(f'/api/v1/tasks/{task.id}/status/', {
                'status': 'IN_PROGRESS', 'expected_status': 'TODO',
            }, format='json').status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(change)
        try:
            assert authorized.wait(10)
            reassigned = api_as(task_users['manager']).patch(f'/api/v1/tasks/{task.id}/', {
                'assignee_id': task_users['employee2'].id, 'expected_updated_at': task.updated_at.isoformat(),
            }, format='json')
            assert reassigned.status_code == 200
        finally:
            proceed.set()
        assert future.result(timeout=10) == 403
    task.refresh_from_db()
    assert task.assignee_id == task_users['employee2'].id
    assert task.status.code == 'TODO'
    assert not TaskAuditLog.objects.filter(task=task, action=TaskAuditLog.Action.STATUS_CHANGED).exists()


@pytest.mark.django_db(transaction=True)
def test_edit_after_concurrent_soft_delete_returns_404_without_side_effects(task_users, task_statuses, task_project, monkeypatch):
    task = make_task(task_project, task_statuses, task_users['employee'])
    validated = Event()
    proceed = Event()
    original = TaskService.update_task

    def delayed_update(*args, **kwargs):
        validated.set()
        assert proceed.wait(10)
        return original(*args, **kwargs)

    monkeypatch.setattr(TaskService, 'update_task', delayed_update)

    def edit():
        close_old_connections()
        try:
            return api_as(task_users['manager']).patch(f'/api/v1/tasks/{task.id}/', {
                'title': 'Changed after delete', 'expected_updated_at': task.updated_at.isoformat(),
            }, format='json').status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(edit)
        try:
            assert validated.wait(10)
            assert api_as(task_users['manager']).delete(f'/api/v1/tasks/{task.id}/').status_code == 204
        finally:
            proceed.set()
        assert future.result(timeout=10) == 404
    task.refresh_from_db()
    assert task.is_deleted and task.title != 'Changed after delete'
    assert not TaskAuditLog.objects.filter(task=task, action=TaskAuditLog.Action.UPDATED).exists()
    assert not Notification.objects.filter(user=task_users['employee'], message__contains='Changed after delete').exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('operation', ['complete', 'delete'])
def test_parent_changes_after_child_validation_block_child_creation(task_users, task_statuses, task_project, monkeypatch, operation):
    parent = make_task(task_project, task_statuses, task_users['employee'])
    validated = Event()
    proceed = Event()
    original = TaskService.create_task

    def delayed_create(validated_data, actor=None):
        validated.set()
        assert proceed.wait(10)
        return original(validated_data, actor)

    monkeypatch.setattr(TaskService, 'create_task', delayed_create)

    def create_child():
        close_old_connections()
        try:
            return api_as(task_users['manager']).post('/api/v1/tasks/', {
                'title': 'Child', 'project_id': task_project.id, 'parent': parent.id,
            }, format='json').status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(create_child)
        try:
            assert validated.wait(10)
            client = api_as(task_users['manager'])
            if operation == 'complete':
                changed = client.patch(f'/api/v1/tasks/{parent.id}/status/', {'status': 'COMPLETED', 'expected_status': 'TODO'}, format='json')
                assert changed.status_code == 200
            else:
                assert client.delete(f'/api/v1/tasks/{parent.id}/').status_code == 204
        finally:
            proceed.set()
        assert future.result(timeout=10) == 400
    assert not Task.objects.filter(parent=parent, is_deleted=False).exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('operation', ['complete', 'delete'])
def test_parent_change_after_inflight_child_creation_is_consistent(task_users, task_statuses, task_project, monkeypatch, operation):
    parent = make_task(task_project, task_statuses, task_users['employee'])
    child_created = Event()
    finish_create = Event()
    from apps.tasks import services
    original_notify = services.create_notification

    def delayed_notify(*args, **kwargs):
        child_created.set()
        assert finish_create.wait(10)
        return original_notify(*args, **kwargs)

    monkeypatch.setattr(services, 'create_notification', delayed_notify)

    def call(action):
        close_old_connections()
        try:
            client = api_as(task_users['manager'])
            if action == 'create':
                return client.post('/api/v1/tasks/', {'title': 'Child', 'project_id': task_project.id, 'parent': parent.id, 'assignee_id': task_users['employee'].id}, format='json').status_code
            if operation == 'complete':
                return client.patch(f'/api/v1/tasks/{parent.id}/status/', {'status': 'COMPLETED', 'expected_status': 'TODO'}, format='json').status_code
            return client.delete(f'/api/v1/tasks/{parent.id}/').status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        creating = executor.submit(call, 'create')
        try:
            assert child_created.wait(10)
            changing = executor.submit(call, 'change')
        finally:
            finish_create.set()
        assert creating.result(timeout=10) == 201
        assert changing.result(timeout=10) == (400 if operation == 'complete' else 204)
    parent.refresh_from_db()
    if operation == 'complete':
        assert parent.status.code != TaskStatus.Code.COMPLETED
        assert Task.objects.filter(parent=parent, is_deleted=False).count() == 1
    else:
        assert parent.is_deleted
        assert not Task.objects.filter(parent=parent, is_deleted=False).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_member_removal_and_task_assignment(task_users, task_statuses, task_project, monkeypatch):
    checked = Event()
    continue_create = Event()
    original = TaskService.create_task

    def delayed_create(validated_data, actor=None):
        checked.set()
        assert continue_create.wait(10)
        return original(validated_data, actor)

    monkeypatch.setattr(TaskService, 'create_task', delayed_create)

    def create():
        close_old_connections()
        try:
            return api_as(task_users['manager']).post('/api/v1/tasks/', {
                'title': 'Concurrent task', 'project_id': task_project.id,
                'assignee_id': task_users['employee'].id,
            }, format='json').status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(create)
        try:
            assert checked.wait(10)
            removed = api_as(task_users['manager']).delete(
                f"/api/v1/projects/{task_project.id}/members/{task_users['employee'].id}/"
            )
            assert removed.status_code == 204
        finally:
            continue_create.set()
        status = future.result(timeout=10)
    assert status == 400
    assert not Task.objects.filter(project=task_project, assignee=task_users['employee'], is_deleted=False).exists()


@pytest.mark.django_db(transaction=True)
def test_member_removal_waits_for_inflight_assignment(task_users, task_statuses, task_project, monkeypatch):
    assigned = Event()
    finish_assignment = Event()
    from apps.tasks import services
    original_notify = services.create_notification

    def delayed_notify(*args, **kwargs):
        assigned.set()
        assert finish_assignment.wait(10)
        return original_notify(*args, **kwargs)

    monkeypatch.setattr(services, 'create_notification', delayed_notify)

    def request(action):
        close_old_connections()
        try:
            client = api_as(task_users['manager'])
            if action == 'create':
                return client.post('/api/v1/tasks/', {'title': 'Concurrent task', 'project_id': task_project.id, 'assignee_id': task_users['employee'].id}, format='json').status_code
            return client.delete(f"/api/v1/projects/{task_project.id}/members/{task_users['employee'].id}/").status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        creating = executor.submit(request, 'create')
        try:
            assert assigned.wait(10)
            removing = executor.submit(request, 'remove')
        finally:
            finish_assignment.set()
        assert creating.result(timeout=10) == 201
        assert removing.result(timeout=10) == 409
    assert ProjectMember.objects.filter(project=task_project, user=task_users['employee']).exists()


@pytest.mark.django_db
def test_creation_audit_records_all_initial_fields_as_json(task_users, task_statuses, task_project):
    parent = make_task(task_project, task_statuses, task_users['employee'])
    today = timezone.localdate()
    payload = {
        'title': 'Audit initial', 'description': 'Nội dung ban đầu', 'project_id': task_project.id,
        'assignee_id': task_users['employee'].id, 'priority': 3, 'parent': parent.id,
        'start_date': today.isoformat(), 'deadline': (today + timedelta(days=3)).isoformat(),
        'estimated_hours': '12.50', 'progress': 35, 'status': 'TODO',
    }
    response = api_as(task_users['manager']).post('/api/v1/tasks/', payload, format='json')
    assert response.status_code == 201
    log = TaskAuditLog.objects.get(task_id=response.data['data']['id'], action=TaskAuditLog.Action.CREATED)
    assert log.changes['description'] == {'old': None, 'new': 'Nội dung ban đầu'}
    assert log.changes['priority']['new'] == 3
    assert log.changes['start_date']['new'] == today.isoformat()
    assert log.changes['estimated_hours']['new'] == '12.50'
    assert log.changes['progress']['new'] == 35
    assert log.changes['parent']['new'] == {'id': parent.id, 'title': parent.title}
    assert log.changes['assignee']['new']['id'] == task_users['employee'].id
    assert log.changes['status']['new'] == 'TODO'


@pytest.mark.django_db
def test_creating_on_hold_requires_reason_and_records_it(task_users, task_statuses, task_project):
    client = api_as(task_users['manager'])
    payload = {'title': 'Paused task', 'project_id': task_project.id, 'status': 'ON_HOLD'}
    assert client.post('/api/v1/tasks/', payload, format='json').status_code == 400
    assert client.post('/api/v1/tasks/', {**payload, 'note': '   '}, format='json').status_code == 400
    response = client.post('/api/v1/tasks/', {**payload, 'note': '  Chờ duyệt  '}, format='json')
    assert response.status_code == 201
    log = TaskAuditLog.objects.get(task_id=response.data['data']['id'], action=TaskAuditLog.Action.CREATED)
    assert log.changes['note']['new'] == 'Chờ duyệt'


@pytest.mark.django_db
def test_task_deadline_cannot_exceed_project_end_date(
    task_users, task_statuses, task_project
):
    project_end = timezone.localdate() + timedelta(days=10)
    task_project.end_date = project_end
    task_project.save(update_fields=["end_date"])
    client = api_as(task_users["manager"])
    payload = {
        "title": "Bounded task",
        "project_id": task_project.id,
        "deadline": project_end.isoformat(),
    }

    created = client.post("/api/v1/tasks/", payload, format="json")
    invalid_create = client.post(
        "/api/v1/tasks/",
        {
            **payload,
            "title": "Too late",
            "deadline": (project_end + timedelta(days=1)).isoformat(),
        },
        format="json",
    )
    invalid_update = client.patch(
        f"/api/v1/tasks/{created.data['data']['id']}/",
        {"deadline": (project_end + timedelta(days=1)).isoformat(), "expected_updated_at": created.data['data']['updated_at']},
        format="json",
    )

    assert created.status_code == 201
    assert invalid_create.status_code == 400
    assert "deadline" in invalid_create.data["errors"]
    assert invalid_update.status_code == 400
    assert "deadline" in invalid_update.data["errors"]


@pytest.mark.django_db
def test_task_list_scope_filters_search_and_hides_deleted(
    task_users, task_statuses, task_project
):
    mine = make_task(
        task_project,
        task_statuses,
        task_users["employee"],
        title="Matching work",
        priority=Task.Priority.HIGH,
    )
    make_task(task_project, task_statuses, task_users["employee2"], title="Other work")
    make_task(
        task_project,
        task_statuses,
        task_users["employee"],
        title="Deleted work",
        is_deleted=True,
    )

    admin = api_as(task_users["admin"]).get("/api/v1/tasks/")
    manager = api_as(task_users["manager2"]).get("/api/v1/tasks/")
    employee = api_as(task_users["employee"]).get(
        f"/api/v1/tasks/?project={task_project.id}&assignee={task_users['employee'].id}"
        f"&status=TODO&priority=3&deadline={mine.deadline}&search=matching"
    )
    outsider = api_as(task_users["outsider"]).get("/api/v1/tasks/")

    assert admin.data["data"]["count"] == 2
    assert manager.data["data"]["count"] == 2
    assert [row["id"] for row in employee.data["data"]["results"]] == [mine.id]
    assert outsider.data["data"]["count"] == 0


@pytest.mark.django_db
def test_task_list_has_bounded_query_count(
    django_assert_max_num_queries, task_users, task_statuses, task_project
):
    for index in range(12):
        make_task(task_project, task_statuses, task_users["employee"], title=f"Task {index}")

    with django_assert_max_num_queries(6):
        response = api_as(task_users["employee"]).get("/api/v1/tasks/?page_size=100")

    assert response.status_code == 200
    assert response.data["data"]["count"] == 12


@pytest.mark.django_db
def test_task_list_supports_deadline_ranges_urgency_filters_and_csv_export(
    task_users, task_statuses, task_project
):
    today = timezone.localdate()
    overdue = make_task(
        task_project, task_statuses, task_users["employee"], title="Overdue", deadline=today - timedelta(days=1)
    )
    soon = make_task(
        task_project, task_statuses, task_users["employee"], title="Due soon", deadline=today + timedelta(days=2)
    )
    make_task(
        task_project, task_statuses, task_users["employee"], title="Later", deadline=today + timedelta(days=5)
    )

    ranged = api_as(task_users["employee"]).get(
        f"/api/v1/tasks/?deadline_from={today}&deadline_to={today + timedelta(days=2)}"
    )
    overdue_response = api_as(task_users["employee"]).get("/api/v1/tasks/?overdue=true")
    soon_response = api_as(task_users["employee"]).get("/api/v1/tasks/?due_soon=true")
    invalid_range = api_as(task_users["employee"]).get(
        f"/api/v1/tasks/?deadline_from={today + timedelta(days=2)}&deadline_to={today}"
    )
    exported = api_as(task_users["employee"]).get("/api/v1/tasks/export/?due_soon=true")

    assert {row["id"] for row in ranged.data["data"]["results"]} == {soon.id}
    assert [row["id"] for row in overdue_response.data["data"]["results"]] == [overdue.id]
    assert soon.id in {row["id"] for row in soon_response.data["data"]["results"]}
    assert invalid_range.status_code == 400
    assert exported.status_code == 200
    assert exported["Content-Type"].startswith("text/csv")
    assert "Due soon" in exported.content.decode("utf-8-sig")
    assert "Later" not in exported.content.decode("utf-8-sig")


@pytest.mark.django_db
def test_task_csv_export_escapes_formula_values(task_users, task_statuses, task_project):
    task_project.name = "@Malicious project"
    task_project.save(update_fields=["name"])
    assignee = task_users["employee"]
    assignee.full_name = "+Malicious assignee"
    assignee.save(update_fields=["full_name"])
    make_task(
        task_project,
        task_statuses,
        assignee,
        title='=HYPERLINK("http://evil","click")',
    )
    make_task(task_project, task_statuses, assignee, title="\t=1+1")
    make_task(task_project, task_statuses, assignee, title="\r=1+1")

    response = api_as(assignee).get("/api/v1/tasks/export/")
    rows = list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))

    formula_row = next(
        row for row in rows[1:] if row[1] == '\'=HYPERLINK("http://evil","click")'
    )
    assert formula_row[1:4] == [
        '\'=HYPERLINK("http://evil","click")',
        "'@Malicious project",
        "'+Malicious assignee",
    ]
    assert {row[1] for row in rows[1:]} >= {"'\t=1+1", "'\r=1+1"}


@pytest.mark.django_db
def test_reassignment_notifies_previous_assignee_without_leaking_to_former_member(task_users, task_statuses, task_project):
    old = task_users['employee']
    new = task_users['employee2']
    task = make_task(task_project, task_statuses, old)
    client = api_as(task_users['manager'])
    updated = client.patch(f'/api/v1/tasks/{task.id}/', {
        'assignee_id': new.id, 'expected_updated_at': task.updated_at.isoformat(),
    }, format='json')
    assert updated.status_code == 200
    assert Notification.objects.filter(user=old, type=NotificationType.GENERAL, message=f'Bạn không còn được phân công công việc "{task.title}".').count() == 1
    assert Notification.objects.filter(user=new, type=NotificationType.TASK_ASSIGNED).count() == 1
    task.refresh_from_db()
    unchanged = client.patch(f'/api/v1/tasks/{task.id}/', {'progress': 10, 'expected_updated_at': task.updated_at.isoformat()}, format='json')
    assert unchanged.status_code == 200
    assert Notification.objects.filter(user=old, type=NotificationType.GENERAL).count() == 1
    task.refresh_from_db()
    removed = client.patch(f'/api/v1/tasks/{task.id}/', {'assignee_id': None, 'expected_updated_at': task.updated_at.isoformat()}, format='json')
    assert removed.status_code == 200
    assert Notification.objects.filter(user=new, type=NotificationType.GENERAL).count() == 1

    completed = make_task(task_project, task_statuses, old, status=task_statuses['COMPLETED'], title='Sensitive')
    ProjectMember.objects.filter(project=task_project, user=old).delete()
    response = client.patch(f'/api/v1/tasks/{completed.id}/', {'assignee_id': new.id, 'expected_updated_at': completed.updated_at.isoformat()}, format='json')
    assert response.status_code == 200
    latest = Notification.objects.filter(user=old, type=NotificationType.GENERAL).latest('id')
    assert 'Sensitive' not in latest.message


@pytest.mark.django_db
def test_important_task_edits_notify_assignee_once_and_rollback_on_failure(task_users, task_statuses, task_project, monkeypatch):
    assignee = task_users['employee']
    task = make_task(task_project, task_statuses, assignee)
    client = api_as(task_users['manager'])
    url = f'/api/v1/tasks/{task.id}/'
    response = client.patch(url, {
        'description': 'Nội dung mới', 'deadline': '2027-01-01', 'priority': 3,
        'expected_updated_at': task.updated_at.isoformat(),
    }, format='json')
    assert response.status_code == 200
    notifications = Notification.objects.filter(user=assignee, type=NotificationType.GENERAL)
    assert notifications.count() == 1
    assert 'nội dung' in notifications.first().message
    assert 'hạn hoàn thành' in notifications.first().message
    assert 'mức ưu tiên' in notifications.first().message
    task.refresh_from_db()
    same = client.patch(url, {'description': task.description, 'expected_updated_at': task.updated_at.isoformat()}, format='json')
    assert same.status_code == 200
    assert notifications.count() == 1

    def fail_notification(*args, **kwargs):
        raise RuntimeError('notification failed')

    monkeypatch.setattr('apps.tasks.services.create_notification', fail_notification)
    task.refresh_from_db()
    with pytest.raises(RuntimeError, match='notification failed'):
        client.patch(url, {'title': 'Updated', 'expected_updated_at': task.updated_at.isoformat()}, format='json')
    task.refresh_from_db()
    assert task.title != 'Updated'


@pytest.mark.django_db
def test_task_update_requires_current_version_and_rejects_stale_changes(task_users, task_statuses, task_project):
    task = make_task(task_project, task_statuses, task_users['employee'])
    client = api_as(task_users['manager'])
    url = f'/api/v1/tasks/{task.id}/'
    version = task.updated_at.isoformat()
    missing = client.patch(url, {'title': 'No version'}, format='json')
    assert missing.status_code == 400
    assert 'expected_updated_at' in missing.data['errors']
    first = client.patch(url, {'description': 'New description', 'expected_updated_at': version}, format='json')
    assert first.status_code == 200
    stale = client.patch(url, {'title': 'Stale title', 'description': 'Old description', 'expected_updated_at': version}, format='json')
    assert stale.status_code == 409
    task.refresh_from_db()
    assert task.description == 'New description'
    assert task.title != 'Stale title'


@pytest.mark.django_db
def test_task_detail_update_delete_permissions_and_soft_delete(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    url = f"/api/v1/tasks/{task.id}/"

    assert api_as(task_users["employee"]).get(url).status_code == 200
    assert api_as(task_users["employee2"]).get(url).status_code == 404
    assert (
        api_as(task_users["manager2"])
        .patch(url, {"title": "Hijacked"}, format="json")
        .status_code
        == 403
    )
    updated = api_as(task_users["manager"]).patch(
        url,
        {
            "title": "Updated safely",
            "expected_updated_at": task.updated_at.isoformat(),
            "assignee_id": task_users["employee2"].id,
            "deadline": "2026-11-01",
        },
        format="json",
    )
    deleted = api_as(task_users["admin"]).delete(url)

    assert updated.status_code == 200
    assert updated.data["data"]["title"] == "Updated safely"
    assert deleted.status_code == 204
    task.refresh_from_db()
    assert task.is_deleted is True
    assert Task.objects.filter(pk=task.pk).exists()
    assert api_as(task_users["manager"]).get(url).status_code == 404


@pytest.mark.django_db
def test_deleted_tasks_and_history_are_available_only_to_admin(task_users, task_statuses, task_project):
    parent = make_task(task_project, task_statuses, task_users['employee'])
    child = make_task(task_project, task_statuses, task_users['employee'], parent=parent)
    active = make_task(task_project, task_statuses, task_users['employee'])
    manager = api_as(task_users['manager'])
    admin = api_as(task_users['admin'])
    assert manager.delete(f'/api/v1/tasks/{parent.id}/').status_code == 204

    response = admin.get('/api/v1/tasks/deleted/?page_size=1')
    assert response.status_code == 200
    assert response.data['data']['count'] == 2
    assert response.data['data']['next'] is not None
    row = response.data['data']['results'][0]
    assert row['id'] in {parent.id, child.id}
    assert row['deleted_by_id'] == task_users['manager'].id
    assert row['deleted_at'] is not None
    history = admin.get(f'/api/v1/tasks/deleted/{child.id}/history/')
    assert history.status_code == 200
    assert any(log['action'] == 'DELETED' and log['actor']['id'] == task_users['manager'].id for log in history.data['data']['results'])
    assert admin.get(f'/api/v1/tasks/{child.id}/history/').status_code == 404
    assert admin.get(f'/api/v1/tasks/deleted/{active.id}/history/').status_code == 404
    for client in (manager, api_as(task_users['employee']), api_as(task_users['outsider'])):
        assert client.get('/api/v1/tasks/deleted/').status_code == 403
        assert client.get(f'/api/v1/tasks/deleted/{child.id}/history/').status_code == 403
    assert api_as().get('/api/v1/tasks/deleted/').status_code in (401, 403)


@pytest.mark.django_db
def test_soft_deleting_parent_soft_deletes_each_subtask(
    task_users, task_statuses, task_project
):
    parent = make_task(task_project, task_statuses, task_users["employee"])
    children = [
        make_task(task_project, task_statuses, task_users["employee"], parent=parent)
        for _ in range(2)
    ]

    response = api_as(task_users["manager"]).delete(f"/api/v1/tasks/{parent.id}/")

    assert response.status_code == 204
    assert all(Task.objects.get(pk=child.pk).is_deleted for child in children)
    assert all(
        TaskAuditLog.objects.filter(task=child, action=TaskAuditLog.Action.DELETED).exists()
        for child in children
    )


@pytest.mark.django_db
def test_task_planning_fields_are_json_safe_in_audit_log(
    task_users, task_statuses, task_project
):
    parent = make_task(task_project, task_statuses, task_users["employee"])
    task = make_task(task_project, task_statuses, task_users["employee2"])
    start_date = timezone.localdate()

    response = api_as(task_users["manager"]).patch(
        f"/api/v1/tasks/{task.id}/",
        {"start_date": start_date.isoformat(), "estimated_hours": "12.50", "parent": parent.id, "expected_updated_at": task.updated_at.isoformat()},
        format="json",
    )

    assert response.status_code == 200
    changes = TaskAuditLog.objects.filter(task=task).latest("id").changes
    assert changes["start_date"]["new"] == start_date.isoformat()
    assert changes["estimated_hours"]["new"] == "12.50"
    assert changes["parent"]["new"] == {"id": parent.id, "title": parent.title}


@pytest.mark.django_db
def test_task_parent_can_have_multiple_direct_subtasks(
    task_users, task_statuses, task_project
):
    parent = make_task(task_project, task_statuses, task_users["employee"])
    payload = {
        "title": "Subtask",
        "project_id": task_project.id,
        "assignee_id": task_users["employee"].id,
        "parent": parent.id,
    }

    first = api_as(task_users["manager"]).post("/api/v1/tasks/", payload, format="json")
    second = api_as(task_users["manager"]).post(
        "/api/v1/tasks/", {**payload, "title": "Another subtask"}, format="json"
    )

    assert first.status_code == 201
    assert second.status_code == 201


@pytest.mark.django_db
def test_checklist_position_is_server_managed(task_users, task_statuses, task_project):
    task = make_task(task_project, task_statuses, task_users["employee"])
    response = api_as(task_users["employee"]).post(
        f"/api/v1/tasks/{task.id}/checklist/",
        {"title": "First item", "position": 7},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["data"]["position"] == 0


@pytest.mark.django_db
def test_task_detail_embeds_checklist_while_list_only_returns_counts(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    TaskChecklistItem.objects.create(task=task, title="First", is_completed=True, position=0)
    TaskChecklistItem.objects.create(task=task, title="Second", position=1)
    client = api_as(task_users["employee"])

    listed = client.get("/api/v1/tasks/?page_size=100")
    detailed = client.get(f"/api/v1/tasks/{task.id}/")

    row = listed.data["data"]["results"][0]
    assert listed.status_code == 200
    assert row["checklist_total"] == 2
    assert row["checklist_done"] == 1
    assert "checklist" not in row
    assert detailed.status_code == 200
    assert [item["title"] for item in detailed.data["data"]["checklist"]] == [
        "First",
        "Second",
    ]
    assert detailed.data["data"]["effective_progress"] == 50
    assert detailed.data["data"]["can_edit_checklist"] is True


@pytest.mark.django_db
def test_task_api_exposes_parent_and_subtask_metadata(
    task_users, task_statuses, task_project
):
    parent = make_task(task_project, task_statuses, task_users["employee"])
    child = make_task(
        task_project,
        task_statuses,
        task_users["employee"],
        parent=parent,
    )

    parent_data = api_as(task_users["manager"]).get(
        f"/api/v1/tasks/{parent.id}/"
    ).data["data"]
    child_data = api_as(task_users["manager"]).get(
        f"/api/v1/tasks/{child.id}/"
    ).data["data"]

    assert parent_data["has_subtasks"] is True
    assert parent_data["parent"] is None
    assert child_data["has_subtasks"] is False
    assert child_data["parent"] == {"id": parent.id, "title": parent.title}


@pytest.mark.django_db
def test_checklist_read_scope_and_write_permission(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    TaskChecklistItem.objects.create(task=task, title="Visible")
    url = f"/api/v1/tasks/{task.id}/checklist/"

    visible = api_as(task_users["manager2"]).get(url)
    forbidden = api_as(task_users["manager2"]).post(
        url, {"title": "Not allowed"}, format="json"
    )
    hidden = api_as(task_users["outsider"]).get(url)

    assert visible.status_code == 200
    assert visible.data["data"][0]["title"] == "Visible"
    assert forbidden.status_code == 403
    assert hidden.status_code == 404
    task_detail = api_as(task_users["manager2"]).get(
        f"/api/v1/tasks/{task.id}/"
    )
    assert task_detail.data["data"]["can_edit_checklist"] is False


@pytest.mark.django_db
def test_checklist_mutations_audit_progress_and_block_completed_tasks(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    client = api_as(task_users["employee"])
    collection_url = f"/api/v1/tasks/{task.id}/checklist/"

    created = client.post(collection_url, {"title": "Review"}, format="json")
    item_id = created.data["data"]["id"]
    item_url = f"{collection_url}{item_id}/"
    updated = client.patch(
        item_url,
        {"title": "Review result", "is_completed": True, "position": 99},
        format="json",
    )
    detail = client.get(f"/api/v1/tasks/{task.id}/")

    assert created.status_code == 201
    assert updated.status_code == 200
    assert updated.data["data"]["position"] == 0
    assert detail.data["data"]["effective_progress"] == 100
    created_log = TaskAuditLog.objects.get(
        task=task, action=TaskAuditLog.Action.CHECKLIST_CREATED
    )
    updated_log = TaskAuditLog.objects.get(
        task=task, action=TaskAuditLog.Action.CHECKLIST_UPDATED
    )
    assert created_log.changes["item"]["title"] == "Review"
    assert updated_log.changes["is_completed"] == {"old": False, "new": True}

    task.status = task_statuses[TaskStatus.Code.COMPLETED]
    task.save(update_fields=["status"])
    completed_detail = client.get(f"/api/v1/tasks/{task.id}/")
    assert completed_detail.data["data"]["can_edit_checklist"] is False
    assert client.post(collection_url, {"title": "Blocked"}, format="json").status_code == 400
    assert client.patch(item_url, {"title": "Blocked"}, format="json").status_code == 400
    assert client.delete(item_url).status_code == 400

    task.status = task_statuses[TaskStatus.Code.IN_PROGRESS]
    task.save(update_fields=["status"])
    assert client.delete(item_url).status_code == 204
    deleted_log = TaskAuditLog.objects.get(
        task=task, action=TaskAuditLog.Action.CHECKLIST_DELETED
    )
    assert deleted_log.changes["item"] == {
        "id": item_id,
        "title": "Review result",
    }


@pytest.mark.django_db
def test_checklist_limit_allows_item_100_and_rejects_item_101(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    TaskChecklistItem.objects.bulk_create(
        [
            TaskChecklistItem(task=task, title=f"Item {index}", position=index)
            for index in range(99)
        ]
    )
    client = api_as(task_users["employee"])
    url = f"/api/v1/tasks/{task.id}/checklist/"

    hundredth = client.post(url, {"title": "Item 100"}, format="json")
    overflow = client.post(url, {"title": "Item 101"}, format="json")

    assert hundredth.status_code == 201
    assert hundredth.data["data"]["position"] == 99
    assert overflow.status_code == 400
    assert task.checklist_items.count() == 100


@pytest.mark.django_db(transaction=True)
def test_concurrent_checklist_creates_cannot_exceed_limit(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    TaskChecklistItem.objects.bulk_create(
        [
            TaskChecklistItem(task=task, title=f"Item {index}", position=index)
            for index in range(99)
        ]
    )
    task_id = task.id
    user_id = task_users["employee"].id

    def create_item(index):
        close_old_connections()
        try:
            user = User.objects.get(pk=user_id)
            response = api_as(user).post(
                f"/api/v1/tasks/{task_id}/checklist/",
                {"title": f"Concurrent {index}"},
                format="json",
            )
            return response.status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = sorted(executor.map(create_item, range(2)))

    assert statuses == [201, 400]
    assert TaskChecklistItem.objects.filter(task_id=task_id).count() == 100


@pytest.mark.django_db
def test_checklist_order_endpoint_only_allows_put(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    url = f"/api/v1/tasks/{task.id}/checklist/order/"
    client = api_as(task_users["employee"])

    assert client.get(url).status_code == 405
    assert client.post(url, {"title": "Sneaky"}, format="json").status_code == 405
    assert task.checklist_items.count() == 0


@pytest.mark.django_db
def test_checklist_reorder_validates_order_audits_and_enforces_permissions(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    items = [
        TaskChecklistItem.objects.create(task=task, title=title, position=index)
        for index, title in enumerate(("A", "B", "C"))
    ]
    url = f"/api/v1/tasks/{task.id}/checklist/order/"
    employee = api_as(task_users["employee"])
    other_task = make_task(task_project, task_statuses, task_users["employee"])
    foreign_item = TaskChecklistItem.objects.create(task=other_task, title="Foreign")

    invalid = employee.put(url, {"item_ids": [items[0].id, items[0].id]}, format="json")
    missing = employee.put(url, {"item_ids": [items[0].id, items[1].id]}, format="json")
    foreign = employee.put(
        url,
        {"item_ids": [items[0].id, items[1].id, foreign_item.id]},
        format="json",
    )
    forbidden = api_as(task_users["manager2"]).put(
        url, {"item_ids": [item.id for item in items]}, format="json"
    )
    ordered_ids = [items[2].id, items[0].id, items[1].id]
    changed = employee.put(url, {"item_ids": ordered_ids}, format="json")

    assert invalid.status_code == 400
    assert missing.status_code == 400
    assert foreign.status_code == 400
    assert forbidden.status_code == 403
    assert changed.status_code == 200
    assert [row["id"] for row in changed.data["data"]] == ordered_ids
    log = TaskAuditLog.objects.get(task=task, action=TaskAuditLog.Action.CHECKLIST_REORDERED)
    assert log.changes["order"] == {
        "old": [item.id for item in items],
        "new": ordered_ids,
    }
    assert log.changes['order_titles'] == {str(item.id): item.title for item in items}

    task.status = task_statuses[TaskStatus.Code.COMPLETED]
    task.save(update_fields=["status"])
    blocked = employee.put(url, {"item_ids": ordered_ids}, format="json")
    assert blocked.status_code == 400


@pytest.mark.django_db
def test_checklist_reorder_rejects_more_than_one_hundred_ids(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    response = api_as(task_users["employee"]).put(
        f"/api/v1/tasks/{task.id}/checklist/order/",
        {"item_ids": list(range(1, 102))},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_deleting_same_checklist_item_twice_returns_not_found(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    created = api_as(task_users["employee"]).post(
        f"/api/v1/tasks/{task.id}/checklist/", {"title": "Item"}, format="json"
    )
    url = f"/api/v1/tasks/{task.id}/checklist/{created.data['data']['id']}/"

    assert api_as(task_users["employee"]).delete(url).status_code == 204
    assert api_as(task_users["employee"]).delete(url).status_code == 404


@pytest.mark.django_db
def test_status_workflow_requires_note_and_limits_reopening(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    url = f"/api/v1/tasks/{task.id}/status/"

    forbidden = api_as(task_users["manager2"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "note": "Bắt đầu."}, format="json"
    )
    invalid = api_as(task_users["employee"]).patch(
        url, {"status": "UNKNOWN"}, format="json"
    )
    missing_note = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "expected_status": "TODO"}, format="json"
    )
    skipped = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.ON_HOLD, "expected_status": "IN_PROGRESS"}, format="json"
    )
    changed = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "expected_status": "IN_PROGRESS", "note": "Đã bắt đầu xử lý."}, format="json"
    )
    completed = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.COMPLETED, "expected_status": "IN_PROGRESS", "note": "Đã hoàn tất."}, format="json"
    )
    employee_reopen = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "expected_status": "COMPLETED", "note": "Cần mở lại."}, format="json"
    )
    manager_reopen = api_as(task_users["manager"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "expected_status": "COMPLETED", "note": "Mở lại để bổ sung."}, format="json"
    )

    assert forbidden.status_code == 403
    assert invalid.status_code == 400
    assert missing_note.status_code == 200
    assert skipped.status_code == 400
    assert changed.status_code == 200
    assert changed.data["data"]["status"]["code"] == TaskStatus.Code.IN_PROGRESS
    assert completed.status_code == 200
    assert employee_reopen.status_code == 403
    assert manager_reopen.status_code == 200
    assert Notification.objects.filter(
        user=task_users["manager"], type=NotificationType.STATUS_CHANGED
    ).exists()
    assert Notification.objects.filter(
        user=task_users["manager"],
        type=NotificationType.STATUS_CHANGED,
        message='Công việc "Implement API" đã chuyển sang trạng thái Đang thực hiện.',
    ).exists()


@pytest.mark.django_db
def test_status_change_rejects_missing_or_stale_expected_status(task_users, task_statuses, task_project):
    task = make_task(task_project, task_statuses, task_users['employee'])
    client = api_as(task_users['employee'])
    url = f'/api/v1/tasks/{task.id}/status/'
    missing = client.patch(url, {'status': 'COMPLETED'}, format='json')
    assert missing.status_code == 400
    changed = client.patch(url, {'status': 'ON_HOLD', 'expected_status': 'TODO', 'note': 'Chờ'}, format='json')
    assert changed.status_code == 200
    stale = client.patch(url, {'status': 'COMPLETED', 'expected_status': 'TODO'}, format='json')
    assert stale.status_code == 409
    task.refresh_from_db()
    assert task.status.code == 'ON_HOLD'


@pytest.mark.django_db
def test_completing_with_incomplete_checklist_requires_explicit_confirmation(task_users, task_statuses, task_project):
    task = make_task(task_project, task_statuses, task_users['employee'])
    TaskChecklistItem.objects.create(task=task, title='Chưa xong', is_completed=False)
    client = api_as(task_users['employee'])
    url = f'/api/v1/tasks/{task.id}/status/'
    rejected = client.patch(url, {'status': 'COMPLETED', 'expected_status': 'TODO'}, format='json')
    assert rejected.status_code == 400
    assert 'confirm_incomplete_checklist' in rejected.data['errors']
    task.refresh_from_db()
    assert task.status.code == 'TODO'
    accepted = client.patch(url, {'status': 'COMPLETED', 'expected_status': 'TODO', 'confirm_incomplete_checklist': True}, format='json')
    assert accepted.status_code == 200
    assert accepted.data['data']['effective_progress'] == 100
    assert accepted.data['data']['checklist_done'] == 0
    log = TaskAuditLog.objects.get(task=task, action=TaskAuditLog.Action.STATUS_CHANGED)
    assert log.changes['checklist_incomplete_confirmed']['new'] is True
    assert log.changes['checklist_unfinished_count']['new'] == 1


@pytest.mark.django_db
def test_completion_with_finished_checklist_does_not_record_unneeded_confirmation(task_users, task_statuses, task_project):
    task = make_task(task_project, task_statuses, task_users['employee'])
    TaskChecklistItem.objects.create(task=task, title='Xong', is_completed=True)
    response = api_as(task_users['employee']).patch(f'/api/v1/tasks/{task.id}/status/', {
        'status': 'COMPLETED', 'expected_status': 'TODO', 'confirm_incomplete_checklist': True,
    }, format='json')
    assert response.status_code == 200
    changes = TaskAuditLog.objects.get(task=task, action=TaskAuditLog.Action.STATUS_CHANGED).changes
    assert 'checklist_incomplete_confirmed' not in changes
    assert 'checklist_unfinished_count' not in changes


@pytest.mark.django_db
def test_optional_status_note_accepts_blank_value(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])

    changed = api_as(task_users["employee"]).patch(
        f"/api/v1/tasks/{task.id}/status/",
        {"status": TaskStatus.Code.IN_PROGRESS, "expected_status": "TODO", "note": ""},
        format="json",
    )

    assert changed.status_code == 200
    log = TaskAuditLog.objects.get(task=task, action=TaskAuditLog.Action.STATUS_CHANGED)
    assert "note" not in log.changes


@pytest.mark.django_db
def test_status_restrictions_explain_blocked_transitions(task_users, task_statuses, task_project):
    manager = api_as(task_users['manager'])
    employee = api_as(task_users['employee'])
    parent = make_task(task_project, task_statuses, task_users['employee'])
    make_task(task_project, task_statuses, task_users['employee2'], parent=parent)
    make_task(task_project, task_statuses, task_users['employee2'], parent=parent)
    data = manager.get(f'/api/v1/tasks/{parent.id}/').data['data']
    assert {'code': 'COMPLETED', 'reason': 'Còn 2 công việc con chưa hoàn thành.'} in data['status_restrictions']
    assert any(item['code'] == 'IN_PROGRESS' for item in data['allowed_transitions'])

    completed = make_task(task_project, task_statuses, task_users['employee'], status=task_statuses['COMPLETED'])
    result = employee.get(f'/api/v1/tasks/{completed.id}/').data['data']
    assert 'Chỉ quản trị viên hoặc quản lý' in result['status_restrictions'][0]['reason']
    ProjectMember.objects.filter(project=task_project, user=task_users['employee']).delete()
    result = manager.get(f'/api/v1/tasks/{completed.id}/').data['data']
    assert 'không còn là thành viên' in result['status_restrictions'][0]['reason']


@pytest.mark.django_db
def test_allowed_transitions_match_status_change_permission(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    url = f"/api/v1/tasks/{task.id}/"

    visible = api_as(task_users["manager2"]).get(url)
    blocked = api_as(task_users["manager2"]).patch(
        f"{url}status/",
        {"status": TaskStatus.Code.IN_PROGRESS},
        format="json",
    )
    allowed = api_as(task_users["employee"]).get(url)

    assert visible.status_code == 200
    assert visible.data["data"]["allowed_transitions"] == []
    assert blocked.status_code == 403
    assert {item["code"] for item in allowed.data["data"]["allowed_transitions"]} == {
        TaskStatus.Code.IN_PROGRESS,
        TaskStatus.Code.ON_HOLD,
        TaskStatus.Code.COMPLETED,
    }


@pytest.mark.django_db
def test_reopening_task_requires_assignee_to_remain_in_project(task_users, task_statuses, task_project):
    employee = task_users['employee']
    task = make_task(task_project, task_statuses, employee, status=task_statuses[TaskStatus.Code.COMPLETED])
    client = api_as(task_users['manager'])
    removed = client.delete(f'/api/v1/projects/{task_project.id}/members/{employee.id}/')
    assert removed.status_code == 204
    detail = client.get(f'/api/v1/tasks/{task.id}/')
    assert not any(item['code'] == TaskStatus.Code.IN_PROGRESS for item in detail.data['data']['allowed_transitions'])
    blocked = client.patch(f'/api/v1/tasks/{task.id}/status/', {'status': 'IN_PROGRESS', 'expected_status': 'COMPLETED', 'note': 'Mở lại'}, format='json')
    assert blocked.status_code == 400
    assert 'không còn là thành viên' in str(blocked.data['errors'])
    task.refresh_from_db()
    assert task.status.code == TaskStatus.Code.COMPLETED
    reassigned = client.patch(f'/api/v1/tasks/{task.id}/', {'assignee_id': task_users['employee2'].id, 'expected_updated_at': task.updated_at.isoformat()}, format='json')
    assert reassigned.status_code == 200
    reopened = client.patch(f'/api/v1/tasks/{task.id}/status/', {'status': 'IN_PROGRESS', 'expected_status': 'COMPLETED', 'note': 'Mở lại'}, format='json')
    assert reopened.status_code == 200


@pytest.mark.django_db
def test_parent_information_respects_task_visibility(task_users, task_statuses, task_project):
    parent = make_task(task_project, task_statuses, task_users['employee2'], title='Tên cha bí mật')
    child = make_task(task_project, task_statuses, task_users['employee'], parent=parent)
    TaskAuditLog.objects.create(task=child, actor=task_users['manager'], action=TaskAuditLog.Action.UPDATED, changes={'parent': {'old': None, 'new': {'id': parent.id, 'title': parent.title}}})
    employee = api_as(task_users['employee'])
    detail = employee.get(f'/api/v1/tasks/{child.id}/').data['data']
    assert detail['parent'] is None
    assert detail['parent_id'] is None
    assert detail['has_hidden_parent'] is True
    listing = employee.get('/api/v1/tasks/').data['data']['results']
    assert all('Tên cha bí mật' not in str(row) for row in listing)
    history = employee.get(f'/api/v1/tasks/{child.id}/history/').data['data']['results']
    assert 'Tên cha bí mật' not in str(history)
    dashboard = employee.get('/api/v1/dashboard/summary/').data['data']['recent_tasks']
    assert 'Tên cha bí mật' not in str(dashboard)
    manager_detail = api_as(task_users['manager']).get(f'/api/v1/tasks/{child.id}/').data['data']
    assert manager_detail['parent'] == {'id': parent.id, 'title': parent.title}
    parent.assignee = task_users['employee']
    parent.save(update_fields=['assignee'])
    visible = employee.get(f'/api/v1/tasks/{child.id}/').data['data']
    assert visible['parent']['title'] == parent.title
    assert visible['has_hidden_parent'] is False


@pytest.mark.django_db
def test_child_of_completed_parent_hides_reopen_transition(
    task_users, task_statuses, task_project
):
    parent = make_task(
        task_project,
        task_statuses,
        task_users["employee"],
        status=task_statuses[TaskStatus.Code.COMPLETED],
    )
    child = make_task(task_project, task_statuses, task_users["employee"], parent=parent)

    response = api_as(task_users["employee"]).get(f"/api/v1/tasks/{child.id}/")

    assert response.status_code == 200
    assert TaskStatus.Code.IN_PROGRESS not in {
        item["code"] for item in response.data["data"]["allowed_transitions"]
    }


@pytest.mark.django_db
def test_completed_child_can_be_edited_without_reassigning_completed_parent(
    task_users, task_statuses, task_project
):
    parent = make_task(
        task_project, task_statuses, task_users["employee"],
        status=task_statuses[TaskStatus.Code.COMPLETED],
    )
    child = make_task(
        task_project, task_statuses, task_users["employee"], parent=parent,
        status=task_statuses[TaskStatus.Code.COMPLETED],
    )
    other = make_task(task_project, task_statuses, task_users["employee"])
    client = api_as(task_users["manager"])

    edited = client.patch(f"/api/v1/tasks/{child.id}/", {"title": "Updated", "expected_updated_at": child.updated_at.isoformat()}, format="json")
    blocked = client.patch(f"/api/v1/tasks/{other.id}/", {"parent": parent.id, "expected_updated_at": other.updated_at.isoformat()}, format="json")

    assert edited.status_code == 200
    child.refresh_from_db()
    assert child.title == "Updated"
    assert child.parent_id == parent.id
    assert blocked.status_code == 400


@pytest.mark.django_db
def test_invalid_completed_transition_returns_bad_request_for_manager(
    task_users, task_statuses, task_project
):
    task = make_task(
        task_project,
        task_statuses,
        task_users["employee"],
        status=task_statuses[TaskStatus.Code.COMPLETED],
    )

    response = api_as(task_users["manager"]).patch(
        f"/api/v1/tasks/{task.id}/status/",
        {"status": TaskStatus.Code.TODO, "expected_status": "COMPLETED"},
        format="json",
    )

    assert response.status_code == 400
    assert "status" in response.data["errors"]


@pytest.mark.django_db
def test_status_change_sets_and_clears_completed_at(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    url = f"/api/v1/tasks/{task.id}/status/"
    before_completion = timezone.now()

    completed = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "expected_status": "TODO", "note": "Đang thực hiện."}, format="json"
    )
    completed = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.COMPLETED, "expected_status": "IN_PROGRESS", "note": "Đã hoàn thành."}, format="json"
    )

    task.refresh_from_db()
    assert completed.status_code == 200
    assert task.completed_at is not None
    assert task.completed_at >= before_completion
    assert completed.data["data"]["completed_at"] is not None

    reopened = api_as(task_users["manager"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "expected_status": "COMPLETED", "note": "Mở lại để kiểm tra."}, format="json"
    )

    task.refresh_from_db()
    assert reopened.status_code == 200
    assert task.completed_at is None
    assert reopened.data["data"]["completed_at"] is None


@pytest.mark.django_db
def test_task_history_records_actor_time_and_before_after_values(
    task_users, task_statuses, task_project
):
    original_deadline = timezone.localdate() + timedelta(days=3)
    task = make_task(
        task_project,
        task_statuses,
        task_users["employee"],
        deadline=original_deadline,
    )
    before_change = timezone.now()

    updated = api_as(task_users["manager"]).patch(
        f"/api/v1/tasks/{task.id}/",
        {
            "assignee_id": task_users["employee2"].id,
            "deadline": "2026-11-01",
            "expected_updated_at": task.updated_at.isoformat(),
        },
        format="json",
    )
    changed = api_as(task_users["employee2"]).patch(
        f"/api/v1/tasks/{task.id}/status/",
        {"status": TaskStatus.Code.IN_PROGRESS, "expected_status": "TODO", "note": "Bắt đầu xử lý."},
        format="json",
    )
    repeated = api_as(task_users["employee2"]).patch(
        f"/api/v1/tasks/{task.id}/status/",
        {"status": TaskStatus.Code.IN_PROGRESS, "expected_status": "IN_PROGRESS"},
        format="json",
    )
    history = api_as(task_users["manager"]).get(
        f"/api/v1/tasks/{task.id}/history/"
    )
    hidden = api_as(task_users["outsider"]).get(
        f"/api/v1/tasks/{task.id}/history/"
    )

    task.refresh_from_db()
    assert updated.status_code == 200
    assert changed.status_code == 200
    assert repeated.status_code == 200
    assert task.updated_at >= before_change
    assert updated.data["data"]["updated_at"] is not None
    assert history.status_code == 200
    assert hidden.status_code == 404
    assert history.data["data"]["count"] == 2
    rows = history.data["data"]["results"]
    assert [row["action"] for row in rows] == [
        TaskAuditLog.Action.STATUS_CHANGED,
        TaskAuditLog.Action.UPDATED,
    ]
    assert rows[0]["actor"]["id"] == task_users["employee2"].id
    assert rows[0]["changes"] == {
        "status": {"old": TaskStatus.Code.TODO, "new": TaskStatus.Code.IN_PROGRESS},
        "note": {"old": None, "new": "Bắt đầu xử lý."},
    }
    assert rows[1]["actor"]["id"] == task_users["manager"].id
    assert rows[1]["changes"] == {
        "assignee": {
            "old": {
                "id": task_users["employee"].id,
                "full_name": task_users["employee"].full_name,
            },
            "new": {
                "id": task_users["employee2"].id,
                "full_name": task_users["employee2"].full_name,
            },
        },
        "deadline": {"old": original_deadline.isoformat(), "new": "2026-11-01"},
    }
    assert all(row["created_at"] for row in rows)


@pytest.mark.django_db(transaction=True)
def test_task_creation_rolls_back_when_notification_fails(
    monkeypatch, task_users, task_statuses, task_project
):
    from apps.tasks.services import TaskService

    def fail_notification(**_kwargs):
        raise RuntimeError("notification unavailable")

    monkeypatch.setattr(Notification.objects, "create", fail_notification)
    with pytest.raises(RuntimeError, match="notification unavailable"):
        TaskService.create_task(
            {
                "title": "Must roll back",
                "project": task_project,
                "assignee": task_users["employee"],
                "status": task_statuses[TaskStatus.Code.TODO],
                "priority": Task.Priority.MEDIUM,
            }
        )

    assert not Task.objects.filter(title="Must roll back").exists()


@pytest.mark.django_db
def test_notifications_are_owner_scoped_and_can_be_marked_read(
    task_users,
):
    own = Notification.objects.create(
        user=task_users["employee"],
        message="Assigned",
        type=NotificationType.TASK_ASSIGNED,
    )
    other = Notification.objects.create(
        user=task_users["employee2"],
        message="Other",
        type=NotificationType.GENERAL,
    )
    client = api_as(task_users["employee"])

    listed = client.get("/api/v1/notifications/?is_read=false")
    hidden = client.patch(f"/api/v1/notifications/{other.id}/read/")
    marked = client.patch(f"/api/v1/notifications/{own.id}/read/")
    Notification.objects.create(
        user=task_users["employee"],
        message="Second",
        type=NotificationType.GENERAL,
    )
    all_read = client.post("/api/v1/notifications/read-all/")

    assert listed.status_code == 200
    assert [row["id"] for row in listed.data["data"]["results"]] == [own.id]
    assert hidden.status_code == 404
    assert marked.status_code == 200
    assert marked.data["data"]["is_read"] is True
    assert all_read.status_code == 200
    assert all_read.data["data"]["updated_count"] == 1
    other.refresh_from_db()
    assert other.is_read is False


@pytest.mark.django_db
def test_task_status_metadata_and_overdue_field(
    task_users, task_statuses, task_project
):
    task = make_task(
        task_project,
        task_statuses,
        task_users["employee"],
        deadline=date.today() - timedelta(days=1),
    )

    metadata = api_as(task_users["employee"]).get(
        "/api/v1/metadata/task-statuses/"
    )
    detail = api_as(task_users["employee"]).get(f"/api/v1/tasks/{task.id}/")

    assert {row["code"] for row in metadata.data["data"]} == set(task_statuses)
    assert detail.data["data"]["is_overdue"] is True


@pytest.mark.django_db
def test_task_assignee_metadata_is_scoped_to_visible_projects(
    task_users, task_project, task_statuses
):
    former = task_users['employee']
    inactive = task_users['employee2']
    make_task(task_project, task_statuses, former, status=task_statuses['COMPLETED'])
    make_task(task_project, task_statuses, inactive)
    ProjectMember.objects.filter(project=task_project, user=former).delete()
    inactive.is_active = False
    inactive.save(update_fields=['is_active'])
    other = Project.objects.create(name='Other project', creator=task_users['admin'])
    make_task(other, task_statuses, task_users['outsider'])
    response = api_as(task_users["manager2"]).get(
        "/api/v1/metadata/task-assignees/"
    )

    assert response.status_code == 200
    rows = {row['id']: row for row in response.data['data']}
    assert set(rows) == {former.id, inactive.id}
    assert rows[former.id]['has_former_project_assignment'] is True
    assert rows[inactive.id]['is_active'] is False
    assert rows[inactive.id]['has_former_project_assignment'] is False
    assert api_as(task_users['manager2']).get(f'/api/v1/tasks/?assignee={former.id}').data['data']['count'] == 1
    assert api_as(former).get('/api/v1/metadata/task-assignees/').data['data'] == []
    assert task_users["outsider"].id not in {
        row["id"] for row in response.data["data"]
    }
