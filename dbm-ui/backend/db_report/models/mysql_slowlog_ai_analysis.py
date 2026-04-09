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


class MysqlSlowlogAiAnalysis(models.Model):
    """MySQL慢日志AI分析结果表"""

    bk_biz_id = models.IntegerField(help_text=_("业务的id"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    cluster_domain = models.CharField(max_length=255, help_text=_("集群域名"))
    instance_role = models.CharField(max_length=64, help_text=_("实例角色"))
    time_window_start = models.DateTimeField(help_text=_("时间窗口开始时间"))
    time_window_end = models.DateTimeField(help_text=_("时间窗口结束时间"))
    instance = models.CharField(max_length=255, help_text=_("实例，为空表示按集群维度分析的"))

    analyze_time = models.DateTimeField(help_text=_("分析时间"))
    analyze_result = models.TextField(help_text=_("分析结果"))

    class Meta:
        managed = True
        app_label = "db_report"
        db_table = "tb_mysql_slowlog_ai_analysis"
        verbose_name = _("MySQL慢日志AI分析结果")
        verbose_name_plural = _("MySQL慢日志AI分析结果")
        index_together = ["cluster_domain", "analyze_time"]

    def __str__(self):
        return f"{self.bk_biz_id}-{self.cluster_domain}-{self.analyze_time}"
