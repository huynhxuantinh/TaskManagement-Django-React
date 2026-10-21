from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tasks", "0007_task_planning_and_checklist")]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="estimated_hours",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=8,
                null=True,
                validators=[MinValueValidator(Decimal("0.01"))],
            ),
        )
    ]
