from django.db import migrations


def normalize_legacy_bcrypt(apps, schema_editor):
    user_model = apps.get_model("accounts", "User")
    for user in user_model.objects.filter(password__startswith="$2").iterator():
        user.password = f"bcrypt${user.password}"
        user.save(update_fields=["password"])


def restore_raw_bcrypt(apps, schema_editor):
    user_model = apps.get_model("accounts", "User")
    for user in user_model.objects.filter(password__startswith="bcrypt$$2").iterator():
        user.password = user.password.removeprefix("bcrypt$")
        user.save(update_fields=["password"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.RunPython(normalize_legacy_bcrypt, restore_raw_bcrypt)]
