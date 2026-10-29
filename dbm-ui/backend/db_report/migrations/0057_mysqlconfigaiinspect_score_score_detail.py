from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db_report", "0056_redisbackupresult_redisbinlogresult"),
    ]

    operations = [
        migrations.AddField(
            model_name="mysqlconfigaiinspect",
            name="score",
            field=models.FloatField(blank=True, default=None, help_text="配置巡检分数，空表示未评分", null=True),
        ),
        migrations.AddField(
            model_name="mysqlconfigaiinspect",
            name="score_detail",
            field=models.JSONField(default=dict, help_text="配置巡检评分依据"),
        ),
    ]
