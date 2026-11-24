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
from backend.db_report.enums.mysql_config_consistency_sub_type import MysqlConfigConsistencySubType
from backend.db_report.report_basemodel import BaseReportABS


class MysqlConfigConsistencyReport(BaseReportABS):
    """MySQL / TenDBCluster 关键配置一致性巡检报告"""

    cluster_id = models.IntegerField(default=0, help_text=_("集群ID"))
    cluster = models.CharField(max_length=255, default="", help_text=_("集群域名"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="", help_text=_("集群类型"))
    subtype = models.CharField(
        max_length=64,
        choices=MysqlConfigConsistencySubType.get_choices(),
        default="",
        help_text=_("检查项"),
    )
    diff_count = models.IntegerField(default=0, help_text=_("差异配置项数量"))
    high_impact_count = models.IntegerField(default=0, help_text=_("高危差异配置项数量"))
    diff_variables = models.JSONField(default=list, help_text=_("差异配置项列表"))
    diff_detail = models.JSONField(default=dict, help_text=_("差异详情JSON"))

    class Meta:
        managed = True
        app_label = "db_report"
        db_table = "tb_mysql_config_consistency_report"
        verbose_name = _("MySQL配置一致性巡检报告")
        verbose_name_plural = _("MySQL配置一致性巡检报告")
        indexes = [
            models.Index(fields=["cluster_id", "subtype", "create_at"], name="idx_cfg_consist_cid_sub_at"),
            models.Index(fields=["cluster_type", "subtype", "create_at"], name="idx_cfg_consist_type_sub_at"),
            models.Index(fields=["state", "create_at"], name="idx_cfg_consist_state_at"),
        ]
        constraints = [
            models.UniqueConstraint(fields=("cluster_id", "subtype"), name="uniq_cfg_consist_cid_sub"),
        ]

    def __str__(self):
        return f"{self.cluster}-{self.subtype}-{self.state}"
