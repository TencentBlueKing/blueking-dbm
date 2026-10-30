from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rollback", "0014_tbtendisrollbackplan"),
    ]

    operations = [
        migrations.AddField(
            model_name="tbtendisrollbackplan",
            name="download_state",
            field=models.JSONField(default=dict, verbose_name="下载窗口与批次台账"),
        ),
    ]
