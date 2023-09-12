# Generated by Django 3.2.19 on 2023-07-18 14:49

from django.db import migrations, models

import backend.db_services.redis.redis_dts.enums.type_enums


class Migration(migrations.Migration):

    dependencies = [
        ("redis_dts", "0007_merge_20230712_1630"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="tbtendisdtsjob",
            name="last_data_check_repair_flow_status",
        ),
        migrations.AlterField(
            model_name="tbtendisdtsjob",
            name="data_check_repair_execution_frequency",
            field=models.CharField(
                choices=[
                    ("once_after_replication", "复制完成后执行一次"),
                    ("once_every_three_days", "每三天一次"),
                    ("once_weekly", "每周一次"),
                ],
                default=backend.db_services.redis.redis_dts.enums.type_enums.DtsDataCheckFreq[
                    "ONCE_AFTER_REPLICATION"
                ],
                max_length=64,
                verbose_name="数据校验修复执行频率",
            ),
        ),
        migrations.AlterField(
            model_name="tbtendisdtsjob",
            name="data_check_repair_type",
            field=models.CharField(
                choices=[
                    ("data_check_and_repair", "数据校验并修复"),
                    ("data_check_only", "仅进行数据校验，不进行修复"),
                    ("no_check_no_repair", "不校验不修复"),
                ],
                default=backend.db_services.redis.redis_dts.enums.type_enums.DtsDataCheckType["DATA_CHECK_AND_REPAIR"],
                max_length=64,
                verbose_name="数据校验修复类型",
            ),
        ),
        migrations.AlterField(
            model_name="tbtendisdtsjob",
            name="dts_bill_type",
            field=models.CharField(
                choices=[
                    ("REDIS_CLUSTER_SHARD_NUM_UPDATE", "集群节点数变更"),
                    ("REDIS_CLUSTER_TYPE_UPDATE", "集群类型变更"),
                    ("REDIS_CLUSTER_DATA_COPY", "集群数据复制"),
                ],
                default="",
                max_length=64,
                verbose_name="DTS单据类型",
            ),
        ),
        migrations.AlterField(
            model_name="tbtendisdtsjob",
            name="dts_copy_type",
            field=models.CharField(
                choices=[
                    ("one_app_diff_cluster", "同一业务不同集群"),
                    ("diff_app_diff_cluster", "不同业务不同集群"),
                    ("copy_from_rollback_temp", "从回滚临时环境复制数据"),
                    ("copy_to_other_system", "同步到其他系统,如迁移到腾讯云"),
                    ("user_built_to_dbm", "业务自建迁移到dbm系统"),
                    ("copy_from_rollback_instance", "从回档实例复制数据"),
                ],
                default="",
                max_length=64,
                verbose_name="DTS数据复制类型",
            ),
        ),
        migrations.AlterField(
            model_name="tbtendisdtsjob",
            name="online_switch_type",
            field=models.CharField(
                choices=[("auto_switch", "自动切换"), ("user_confirm", "用户确认切换")],
                default=backend.db_services.redis.redis_dts.enums.type_enums.DtsOnlineSwitchType["USER_CONFIRM"],
                max_length=64,
                verbose_name="在线切换类型",
            ),
        ),
        migrations.AlterField(
            model_name="tbtendisdtsjob",
            name="sync_disconnect_reminder_frequency",
            field=models.CharField(
                choices=[("once_daily", "每天一次"), ("once_weekly", "每周一次")],
                default="",
                max_length=64,
                verbose_name="同步断开提醒频率",
            ),
        ),
        migrations.AlterField(
            model_name="tbtendisdtsjob",
            name="sync_disconnect_type",
            field=models.CharField(
                choices=[
                    ("auto_disconnect_after_replication", "复制完成后自动断开同步关系"),
                    ("keep_sync_with_reminder", "复制完成后保持同步关系，定时发送断开同步提醒"),
                ],
                default="",
                max_length=64,
                verbose_name="同步断开类型",
            ),
        ),
        migrations.AlterField(
            model_name="tbtendisdtsjob",
            name="write_mode",
            field=models.CharField(
                choices=[
                    ("delete_and_write_to_redis", "先删除同名redis key, 再执行写入(如:del $key + hset $key)"),
                    ("keep_and_append_to_redis", "保留同名redis key,追加写入(如hset $key)"),
                    ("flushall_and_write_to_redis", "先清空目标集群所有数据,在写入(如flushall + hset $key)"),
                ],
                default="",
                max_length=64,
                verbose_name="写入模式",
            ),
        ),
        migrations.AlterField(
            model_name="tbtendisdtstask",
            name="write_mode",
            field=models.CharField(
                choices=[
                    ("delete_and_write_to_redis", "先删除同名redis key, 再执行写入(如:del $key + hset $key)"),
                    ("keep_and_append_to_redis", "保留同名redis key,追加写入(如hset $key)"),
                    ("flushall_and_write_to_redis", "先清空目标集群所有数据,在写入(如flushall + hset $key)"),
                ],
                default="",
                max_length=64,
                verbose_name="写入模式",
            ),
        ),
    ]
