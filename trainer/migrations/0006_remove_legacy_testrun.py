from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("trainer", "0005_pageschema_bug_mode"),
    ]

    operations = [
        migrations.DeleteModel(
            name="TestRun",
        ),
    ]
