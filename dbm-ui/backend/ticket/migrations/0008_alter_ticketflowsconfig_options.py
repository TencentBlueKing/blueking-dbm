# Generated by Django 3.2.25 on 2024-06-02 12:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ticket", "0007_merge_20240524_1507"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="ticketflowsconfig",
            options={"verbose_name": "单据流程配置", "verbose_name_plural": "单据流程配置"},
        ),
    ]
