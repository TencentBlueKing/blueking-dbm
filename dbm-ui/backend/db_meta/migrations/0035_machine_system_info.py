# Generated by Django 3.2.19 on 2024-03-12 08:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db_meta", "0034_merge_0033_alter_cluster_name_0033_sqlserverdtsinfo"),
    ]

    operations = [
        migrations.AddField(
            model_name="machine",
            name="system_info",
            field=models.JSONField(default=dict, help_text="机器采集的系统信息"),
        ),
    ]
