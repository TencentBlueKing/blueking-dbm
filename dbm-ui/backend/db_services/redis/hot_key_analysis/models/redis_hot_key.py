"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType
from backend.flow.consts import StateType

logger = logging.getLogger("root")


class RedisHotKeyRecord(AuditedModel):
    """
    定义redis热key记录表，存储redis生成每一条分析报告信息
    redis专属
    """

    bk_biz_id = models.IntegerField(default=0, help_text=_("关联的业务id，对应cmdb"))
    ins_list = models.JSONField(help_text=_("实例列表"), blank=True, null=True, default=list)
    cluster_id = models.IntegerField(default=0, help_text=_("集群ID"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    immute_domain = models.CharField(max_length=255, default="")
    analysis_time = models.IntegerField(default=10, help_text=_("分析时长"))
    ticket_id = models.PositiveIntegerField(default=0, help_text=_("关联的单据id"))
    root_id = models.CharField(max_length=64, default="", help_text=_("关联root_id"))
    status = models.CharField(
        max_length=64, choices=StateType.get_choices(), default=StateType.READY, help_text=_("状态")
    )

    class Meta:
        db_table = "tb_redis_hot_key_record"
        verbose_name = verbose_name_plural = _("redis 热key分析记录表")


class RedisHotKeyRecordDetail(AuditedModel):
    """
    定义redis热key分析详情记录表，存储redis生成每一条分析报告详情信息
    redis专属
    """

    ticket_id = models.BigIntegerField(default=0, help_text=_("关联的单据id"))
    record_id = models.BigIntegerField(default=0, help_text=_("关联的记录id"))
    bk_biz_id = models.IntegerField(default=0, help_text=_("关联的业务id，对应cmdb"))
    cluster_id = models.IntegerField(default=0, help_text=_("集群ID"))
    ins = models.CharField(max_length=255, default="", help_text=_("实例"))
    key = models.CharField(max_length=255, default="", help_text=_("key"))
    cmd_info = models.CharField(max_length=255, default="", help_text=_("执行命令"))
    exec_count = models.IntegerField(default=0, help_text=_("数量"))
    ratio = models.CharField(max_length=64, default="", help_text=_("执行占比"))

    class Meta:
        db_table = "tb_redis_hot_key_record_detail"
        verbose_name = verbose_name_plural = _("redis 热key分析记录详情表")
