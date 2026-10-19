from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0002_alter_task_priority_alter_taskstatus_code'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='taskstatus',
            name='legacy_id',
        ),
    ]
