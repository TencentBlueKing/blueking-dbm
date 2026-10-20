from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db_report", "0054_merge_20260902_1224"),
    ]

    operations = [
        migrations.AddField(
            model_name="esaccountreport",
            name="major_version",
            field=models.CharField(default="", max_length=100, verbose_name="版本"),
        ),
    ]
