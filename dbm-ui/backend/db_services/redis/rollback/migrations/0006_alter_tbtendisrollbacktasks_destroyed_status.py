# Generated by Django 3.2.19 on 2023-07-26 09:41

from django.db import migrations, models

import backend.db_meta.enums.destroyed_status


class Migration(migrations.Migration):

    dependencies = [
        ("rollback", "0005_auto_20230726_1536"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tbtendisrollbacktasks",
            name="destroyed_status",
            field=models.IntegerField(
                choices=[(0, "NOT_DESTROYED"), (1, "DESTROYED"), (2, "DESTROYING")],
                default=backend.db_meta.enums.destroyed_status.DestroyedStatus["NOT_DESTROYED"],
                verbose_name="销毁状态",
            ),
        ),
    ]
