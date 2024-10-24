# Generated by Django 3.2.25 on 2024-08-21 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ticket", "0010_flow_context"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticketflowsconfig",
            name="cluster_ids",
            field=models.JSONField(default=list, verbose_name="集群ID列表"),
        ),
        migrations.AlterField(
            model_name="ticketflowsconfig",
            name="editable",
            field=models.BooleanField(default=True, verbose_name="是否支持用户配置"),
        ),
        migrations.AddIndex(
            model_name="ticketflowsconfig",
            index=models.Index(fields=["bk_biz_id"], name="ticket_tick_bk_biz__593de9_idx"),
        ),
    ]
