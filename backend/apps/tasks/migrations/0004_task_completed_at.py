from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0003_remove_taskstatus_legacy_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
