# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _


class DtsBillType(str, StructuredEnum):
    """
    DTS单据类型
    """

    REDIS_CLUSTER_SHARD_NUM_UPDATE = EnumField("REDIS_CLUSTER_SHARD_NUM_UPDATE", _("集群节点数变更"))
    REDIS_CLUSTER_TYPE_UPDATE = EnumField("REDIS_CLUSTER_TYPE_UPDATE", _("集群类型变更"))
    REDIS_CLUSTER_DATA_COPY = EnumField("REDIS_CLUSTER_DATA_COPY", _("集群数据复制"))


class DtsCopyType(str, StructuredEnum):
    """
    DTS数据复制类型(此时 dts_bill_type=REDIS_CLUSTER_DATA_COPY)
    """

    ONE_APP_DIFF_CLUSTER = EnumField("one_app_diff_cluster", _("业务内"))
    DIFF_APP_DIFF_CLUSTER = EnumField("diff_app_diff_cluster", _("跨业务"))
    COPY_FROM_ROLLBACK_TEMP = EnumField("copy_from_rollback_temp", _("从回滚临时环境复制数据"))
    COPY_TO_OTHER_SYSTEM = EnumField("copy_to_other_system", _("业务内至第三方"))
    USER_BUILT_TO_DBM = EnumField("user_built_to_dbm", _("自建集群至业务内"))
    COPY_FROM_ROLLBACK_INSTANCE = EnumField("copy_from_rollback_instance", _("构造实例至业务内"))


class DtsWriteMode(str, StructuredEnum):
    """
    写入模式
    """

    DELETE_AND_WRITE_TO_REDIS = EnumField(
        "delete_and_write_to_redis", _("先删除同名redis key, 再执行写入(如:del $key + hset $key)")
    )
    KEEP_AND_APPEND_TO_REDIS = EnumField("keep_and_append_to_redis", _("保留同名redis key,追加写入(如hset $key)"))
    FLUSHALL_AND_WRITE_TO_REDIS = EnumField("flushall_and_write_to_redis", _("先清空目标集群所有数据,在写入(如flushall + hset $key)"))


class ExecuteMode(str, StructuredEnum):
    """
    执行模式
    """

    AUTO_EXECUTION = EnumField("auto_execution", _("自动执行"))
    SCHEDULED_EXECUTION = EnumField("scheduled_execution", _("定时执行"))


class DtsOnlineSwitchType(str, StructuredEnum):
    """DTS在线切换类型"""

    AUTO_SWITCH = EnumField("auto_switch", _("自动切换"))
    MANUAL_CONFIRM = EnumField("manual_confirm", _("用户确认切换"))


class DtsSyncDisconnType(str, StructuredEnum):
    """
    同步断开类型
    """

    AUTO_DISCONNECT_AFTER_REPLICATION = EnumField("auto_disconnect_after_replication", _("复制完成后自动断开同步关系"))
    KEEP_SYNC_WITH_REMINDER = EnumField("keep_sync_with_reminder", _("复制完成后保持同步关系，定时发送断开同步提醒"))


class DtsSyncDisconnReminderFreq(str, StructuredEnum):
    """
    Dts复制同步提醒频率
    """

    ONCE_DAILY = EnumField("once_daily", _("每天一次"))
    ONCE_WEEKLY = EnumField("once_weekly", _("每周一次"))


class DtsDataCheckType(str, StructuredEnum):
    """
    数据校验修复类型
    """

    DATA_CHECK_AND_REPAIR = EnumField("data_check_and_repair", _("数据校验并修复"))
    DATA_CHECK_ONLY = EnumField("data_check_only", _("仅进行数据校验，不进行修复"))
    NO_CHECK_NO_REPAIR = EnumField("no_check_no_repair", _("不校验不修复"))


class DtsDataCheckFreq(str, StructuredEnum):
    """
    Dts数据校验修复频率
    """

    ONCE_AFTER_REPLICATION = EnumField("once_after_replication", _("复制完成后执行一次"))
    ONCE_EVERY_THREE_DAYS = EnumField("once_every_three_days", _("每三天一次"))
    ONCE_WEEKLY = EnumField("once_weekly", _("每周一次"))


class DtsDataRepairMode(str, StructuredEnum):
    """
    Dts数据修复模式
    """

    AUTO_REPAIR = EnumField("auto_repair", _("自动修复"))
    MANUAL_CONFIRM = EnumField("manual_confirm", _("用户确认"))


class TimeoutVars(str, StructuredEnum):
    """
    超时时间
    """

    NEVER = EnumField("never", _("永不超时"))
    ONE_HOUR = EnumField("1hour", _("1小时"))
    THREE_HOURS = EnumField("3hours", _("3小时"))
    SIX_HOURS = EnumField("6hours", _("6小时"))
    ONE_DAY = EnumField("1day", _("1天"))
    TWO_DAYS = EnumField("2days", _("2天"))
    ONE_WEEK = EnumField("1week", _("1周"))


class DtsSyncStatus(str, StructuredEnum):
    """
    数据sync 状态
    """

    IN_FULL_TRANSFER = EnumField("in_full_transfer", _("全量传输中"))
    IN_INCREMENTAL_SYNC = EnumField("in_incremental_sync", _("增量同步中"))
    FULL_TRANSFER_FAILED = EnumField("full_transfer_failed", _("全量传输失败"))
    INCREMENTAL_SYNC_FAILED = EnumField("incremental_sync_failed", _("增量同步失败"))
    PENDING_EXECUTION = EnumField("pending_execution", _("待执行"))
    TRANSFER_COMPLETED = EnumField("transfer_completed", _("传输已完成"))
    TRANSFER_TERMINATED = EnumField("transfer_terminated", _("传输被终止"))
    UNKNOWN = EnumField("unknown", _("未知状态"))
