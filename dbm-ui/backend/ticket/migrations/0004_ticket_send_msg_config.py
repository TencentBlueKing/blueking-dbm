# Generated by Django 3.2.19 on 2024-01-21 16:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ticket", "0003_auto_20231201_2032"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="send_msg_config",
            field=models.JSONField(default=dict, verbose_name="单据通知设置"),
        ),
    ]
