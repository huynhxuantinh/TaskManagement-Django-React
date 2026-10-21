from django.core.validators import MaxValueValidator
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("tasks", "0006_alter_task_updated_at")]

    operations = [
        migrations.AddField(
            model_name="task",
            name="estimated_hours",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="parent",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="subtasks", to="tasks.task"),
        ),
        migrations.AddField(
            model_name="task",
            name="progress",
            field=models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)]),
        ),
        migrations.AddField(
            model_name="task",
            name="start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="TaskChecklistItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=300)),
                ("is_completed", models.BooleanField(default=False)),
                ("position", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="checklist_items", to="tasks.task")),
            ],
            options={"ordering": ["position", "id"]},
        ),
    ]
