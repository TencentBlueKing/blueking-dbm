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
from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.db_services.redis.redis_dts.enums import (
    DtsBillType,
    DtsCopyType,
    DtsDataCheckFreq,
    DtsDataCheckType,
    DtsOnlineSwitchType,
    DtsSyncDisconnReminderFreq,
    DtsSyncDisconnType,
    DtsWriteMode,
)


class TbTendisDTSJob(models.Model):
    id = models.BigAutoField(primary_key=True)
    bill_id = models.BigIntegerField(default=0, db_index=True, verbose_name=_("单据号"))
    app = models.CharField(max_length=64, default="", verbose_name=_("业务bk_biz_id"))
    bk_cloud_id = models.BigIntegerField(default=0, verbose_name=_("云区域id"))
    user = models.CharField(max_length=64, default="", verbose_name=_("申请人"))
    dts_bill_type = models.CharField(
        max_length=64, choices=DtsBillType.get_choices(), default="", verbose_name=_("DTS单据类型")
    )
    dts_copy_type = models.CharField(
        max_length=64, choices=DtsCopyType.get_choices(), default="", verbose_name=_("DTS数据复制类型")
    )
    write_mode = models.CharField(
        max_length=64, choices=DtsWriteMode.get_choices(), default="", verbose_name=_("写入模式")
    )
    online_switch_type = models.CharField(
        max_length=64,
        choices=DtsOnlineSwitchType.get_choices(),
        default=DtsOnlineSwitchType.USER_CONFIRM,
        verbose_name=_("在线切换类型"),
    )
    sync_disconnect_type = models.CharField(
        max_length=64, choices=DtsSyncDisconnType.get_choices(), default="", verbose_name=_("同步断开类型")
    )
    sync_disconnect_reminder_frequency = models.CharField(
        max_length=64, choices=DtsSyncDisconnReminderFreq.get_choices(), default="", verbose_name=_("同步断开提醒频率")
    )
    data_check_repair_type = models.CharField(
        max_length=64,
        choices=DtsDataCheckType.get_choices(),
        default=DtsDataCheckType.DATA_CHECK_AND_REPAIR,
        verbose_name=_("数据校验修复类型"),
    )
    data_check_repair_execution_frequency = models.CharField(
        max_length=64,
        choices=DtsDataCheckFreq.get_choices(),
        default=DtsDataCheckFreq.ONCE_AFTER_REPLICATION,
        verbose_name=_("数据校验修复执行频率"),
    )
    # 最近一次数据校验与修复 flow id
    last_data_check_repair_flow_id = models.CharField(max_length=64, default="", verbose_name=_("最近一次数据校验与修复 flow id"))
    # 最近一次数据校验与修复 单据执行时间
    last_data_check_repair_flow_execute_time = models.DateTimeField(null=True, verbose_name=_("最近一次数据校验与修复 单据执行时间"))

    online_switch_flow_id = models.CharField(max_length=64, default="", verbose_name=_("在线切换 flow id"))

    dst_cluster_close_flow_id = models.CharField(max_length=64, default="", verbose_name=_("目的集群禁用 flow id"))
    dst_cluster_shutdown_flow_id = models.CharField(max_length=64, default="", verbose_name=_("目的集群下架 flow id"))

    src_cluster = models.CharField(max_length=128, default="", verbose_name=_("源集群"))
    src_cluster_id = models.BigIntegerField(default=0, verbose_name=_("源集群id"))
    # 源集群类型,如 PredixyTendisplusCluster、TwemproxyTendisSSDInstance
    src_cluster_type = models.CharField(max_length=64, default="", verbose_name=_("源集群类型"))
    src_rollback_bill_id = models.BigIntegerField(default=0, verbose_name=_("回滚单据号"))
    src_rollback_instances = models.TextField(default="", verbose_name=_("回滚临时环境实例"))
    dst_bk_biz_id = models.CharField(max_length=64, default="", verbose_name=_("目标业务id"))
    dst_cluster = models.CharField(max_length=128, default="", verbose_name=_("目的集群"))
    dst_cluster_id = models.BigIntegerField(default=0, verbose_name=_("目的集群id"))
    # 目标集群类型,如 PredixyTendisplusCluster、TwemproxyTendisSSDInstance
    dst_cluster_type = models.CharField(max_length=64, default="", verbose_name=_("目标集群类型"))
    key_white_regex = models.TextField(default="", verbose_name=_("key正则(包含key)"))
    key_black_regex = models.TextField(default="", verbose_name=_("key正则(排除key)"))
    # 任务状态,该字段没用了
    status = models.IntegerField(default=0, db_index=True, verbose_name=_("任务状态"))
    reason = models.TextField(default="", verbose_name=_("备注"))
    create_time = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("创建时间"))
    update_time = models.DateTimeField(auto_now=True, verbose_name=_("更新时间"))

    class Meta:
        db_table = "tb_tendis_dts_job"
        verbose_name = "tb_tendis_dts_job"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=["bill_id", "src_cluster", "dst_cluster"], name="unique_dts_job_key")
        ]
