# Generated by Django 3.2.19 on 2023-06-29 03:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("redis_dts", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="tbtendisdtsjob",
            name="datacheck",
        ),
        migrations.RemoveField(
            model_name="tbtendisdtsjob",
            name="datarepair",
        ),
        migrations.RemoveField(
            model_name="tbtendisdtsjob",
            name="datarepair_mode",
        ),
        migrations.AddField(
            model_name="tbtendisdtsjob",
            name="data_check_repair_execution_frequency",
            field=models.CharField(default="", max_length=64, verbose_name="数据校验修复执行频率"),
        ),
        migrations.AddField(
            model_name="tbtendisdtsjob",
            name="data_check_repair_type",
            field=models.CharField(default="", max_length=64, verbose_name="数据校验修复类型"),
        ),
        migrations.AddField(
            model_name="tbtendisdtsjob",
            name="last_data_check_repair_bill_id",
            field=models.BigIntegerField(default=0, verbose_name="最近一次数据校验与修复 单据id"),
        ),
        migrations.AddField(
            model_name="tbtendisdtsjob",
            name="last_data_check_repair_bill_status",
            field=models.IntegerField(default=0, verbose_name="最近一次数据校验与修复 单据状态"),
        ),
        migrations.AddField(
            model_name="tbtendisdtsjob",
            name="sync_disconnect_reminder_frequency",
            field=models.CharField(default="", max_length=64, verbose_name="同步断开提醒频率"),
        ),
        migrations.AddField(
            model_name="tbtendisdtsjob",
            name="sync_disconnect_type",
            field=models.CharField(default="", max_length=64, verbose_name="同步断开类型"),
        ),
        migrations.AddField(
            model_name="tbtendisdtsjob",
            name="write_mode",
            field=models.CharField(default="", max_length=64, verbose_name="写入模式"),
        ),
        migrations.AddField(
            model_name="tbtendisdtstask",
            name="write_mode",
            field=models.CharField(default="", max_length=64, verbose_name="写入模式"),
        ),
        migrations.AlterField(
            model_name="tbtendisdtsjob",
            name="reason",
            field=models.BinaryField(default=b"", verbose_name="备注"),
        ),
    ]
