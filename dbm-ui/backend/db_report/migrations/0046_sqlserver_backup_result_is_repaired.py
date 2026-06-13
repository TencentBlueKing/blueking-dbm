# Generated for backup auto-repair feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db_report", "0045_mysqlconfigcheckresult"),
    ]

    operations = [
        migrations.AddField(
            model_name="sqlserverbackupresult",
            name="is_repaired",
            field=models.BooleanField(default=False, verbose_name="是否为巡检自动补录"),
        ),
        migrations.AddField(
            model_name="sqlserverbinlogresult",
            name="is_repaired",
            field=models.BooleanField(default=False, verbose_name="是否为巡检自动补录"),
        ),
    ]
