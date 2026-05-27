from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("trainer", "0002_testrunsession_testrunresult"),
    ]

    operations = [
        migrations.AddField(
            model_name="pageschema",
            name="is_public",
            field=models.BooleanField(default=False, verbose_name="Публичная форма"),
        ),
    ]
