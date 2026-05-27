from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("trainer", "0003_pageschema_is_public"),
    ]

    operations = [
        migrations.AddField(
            model_name="fieldschema",
            name="max_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="fieldschema",
            name="max_value",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="fieldschema",
            name="min_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="fieldschema",
            name="min_value",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="fieldschema",
            name="select_options",
            field=models.TextField(
                blank=True,
                help_text="Каждый вариант с новой строки",
            ),
        ),
    ]
