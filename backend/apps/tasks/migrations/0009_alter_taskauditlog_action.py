from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tasks", "0008_alter_task_estimated_hours")]

    operations = [
        migrations.AlterField(
            model_name="taskauditlog",
            name="action",
            field=models.CharField(
                choices=[
                    ("CREATED", "Tạo công việc"), ("UPDATED", "Cập nhật công việc"),
                    ("STATUS_CHANGED", "Đổi trạng thái"), ("DELETED", "Xóa công việc"),
                    ("CHECKLIST_CREATED", "Thêm checklist"), ("CHECKLIST_UPDATED", "Cập nhật checklist"),
                    ("CHECKLIST_DELETED", "Xóa checklist"), ("CHECKLIST_REORDERED", "Sắp xếp checklist"),
                ], max_length=30,
            ),
        )
    ]
