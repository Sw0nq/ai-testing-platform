from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("trainer", "0004_fieldschema_type_specific_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="pageschema",
            name="bug_mode_enabled",
            field=models.BooleanField(
                default=False,
                verbose_name="Режим учебных дефектов",
            ),
        ),
        migrations.AddField(
            model_name="pageschema",
            name="bug_profile",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
