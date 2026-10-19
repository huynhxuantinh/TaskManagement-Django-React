from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_user_username_user_accounts_user_username_ci_uniq'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='role',
            name='legacy_id',
        ),
    ]
