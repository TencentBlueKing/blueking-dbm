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

from backend.db_meta.enums import ClusterType


class MysqlConfigCheckResult(models.Model):
    """集群配置巡检结果表"""

    bk_biz_id = models.IntegerField(help_text=_("业务的id"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="", help_text=_("集群类型"))
    cluster_id = models.IntegerField(default=0, help_text=_("集群ID"))
    cluster_domain = models.CharField(max_length=255, help_text=_("集群域名"))
    cluster_snapshot = models.JSONField(default=dict, help_text=_("集群基础信息快照"))
    analyze_result = models.JSONField(default=dict, help_text=_("分析结果"))
    analyze_time = models.DateTimeField(help_text=_("分析时间"))

    class Meta:
        managed = True
        app_label = "db_report"
        db_table = "tb_tendb_config_check_result"
        verbose_name = _("集群配置巡检结果")
        verbose_name_plural = _("集群配置巡检结果")
        indexes = [
            models.Index(fields=["cluster_id", "analyze_time"]),
            models.Index(fields=["cluster_domain", "analyze_time"]),
        ]

    def __str__(self):
        return f"{self.bk_biz_id}-{self.cluster_domain}-{self.analyze_time}"
