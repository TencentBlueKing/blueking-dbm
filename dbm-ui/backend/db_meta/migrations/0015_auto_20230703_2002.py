# Generated by Django 3.2.19 on 2023-07-03 12:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db_meta", "0014_auto_20230627_1716"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="cluster",
            name="deploy_plan_id",
        ),
        migrations.AddField(
            model_name="spec",
            name="qps",
            field=models.JSONField(default=dict, help_text="qps规格描述:{'min': 1, 'max': 100}"),
        ),
    ]
