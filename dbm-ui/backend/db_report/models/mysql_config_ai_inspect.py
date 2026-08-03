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
from django.utils.translation import gettext_lazy as _

from backend.bk_web.models import AuditedModel
from backend.db_meta.enums import ClusterType
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class MysqlConfigAiInspectStatus(StrStructuredEnum):
    PENDING = EnumField("pending", _("待处理"))
    RUNNING = EnumField("running", _("执行中"))
    SUCCESS = EnumField("success", _("成功"))
    FAILED = EnumField("failed", _("失败"))


class MysqlConfigAiInspect(AuditedModel):
    """MySQL 配置 AI 巡检明细（批次 × 集群）"""

    batch_id = models.CharField(max_length=64, default="", help_text=_("批次 ID"))
    bk_biz_id = models.IntegerField(default=0, help_text=_("业务 ID"))
    cluster_id = models.IntegerField(default=0, help_text=_("集群 ID"))
    cluster_domain = models.CharField(max_length=255, default="", help_text=_("集群域名"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="", help_text=_("集群类型"))
    status = models.CharField(
        max_length=32,
        choices=MysqlConfigAiInspectStatus.get_choices(),
        default=MysqlConfigAiInspectStatus.PENDING.value,
        help_text=_("巡检状态"),
    )
    retry_count = models.IntegerField(default=0, help_text=_("已尝试次数"))
    report_id = models.CharField(max_length=64, default="", help_text=_("报告 ID"))
    share_url = models.CharField(max_length=512, default="", help_text=_("报告分享完整链接"))
    summary = models.TextField(default="", help_text=_("巡检总结"))
    agent_cost_ms = models.IntegerField(default=0, help_text=_("Agent 耗时（毫秒）"))
    error_msg = models.TextField(default="", help_text=_("失败原因"))

    class Meta:
        managed = True
        app_label = "db_report"
        db_table = "tb_mysql_config_ai_inspect"
        verbose_name = _("MySQL配置AI巡检")
        verbose_name_plural = _("MySQL配置AI巡检")
        constraints = [
            models.UniqueConstraint(fields=["batch_id", "cluster_id"], name="uniq_cfg_ai_insp_batch_cluster"),
        ]
        indexes = [
            models.Index(fields=["batch_id", "status"], name="idx_cfg_ai_insp_batch_status"),
            models.Index(fields=["cluster_domain", "create_at"], name="idx_cfg_ai_insp_domain_create"),
        ]

    def __str__(self):
        return f"{self.batch_id}-{self.cluster_domain}-{self.status}"
