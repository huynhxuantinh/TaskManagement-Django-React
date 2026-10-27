from django.db import migrations


def seed_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    labels = {
        "ADMIN": "Quản trị viên",
        "MANAGER": "Quản lý",
        "EMPLOYEE": "Nhân viên",
    }
    for code, name in labels.items():
        Role.objects.update_or_create(code=code, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_remove_role_legacy_id")]
    operations = [migrations.RunPython(seed_roles, migrations.RunPython.noop)]
