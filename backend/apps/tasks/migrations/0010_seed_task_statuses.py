from django.db import migrations


def seed_task_statuses(apps, schema_editor):
    TaskStatus = apps.get_model("tasks", "TaskStatus")
    labels = {
        "TODO": "Chưa thực hiện",
        "IN_PROGRESS": "Đang thực hiện",
        "COMPLETED": "Đã hoàn thành",
        "ON_HOLD": "Tạm dừng",
    }
    for code, name in labels.items():
        TaskStatus.objects.update_or_create(code=code, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [("tasks", "0009_alter_taskauditlog_action")]
    operations = [migrations.RunPython(seed_task_statuses, migrations.RunPython.noop)]
