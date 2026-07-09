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


class MysqlClusterSkewReport(AuditedModel):
    bk_biz_id = models.IntegerField(default=0, help_text=_("业务 ID"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="", help_text=_("集群类型"))
    cluster_domain = models.CharField(max_length=255, default="", help_text=_("集群域名"))
    report_from = models.DateTimeField(help_text=_("报告时间段起始"))
    report_to = models.DateTimeField(help_text=_("报告时间段结束"))
    summary = models.TextField(default="", help_text=_("报告摘要"))
    share_url = models.CharField(max_length=512, default="", help_text=_("报告分享链接"))

    class Meta:
        indexes = [
            models.Index(fields=["cluster_domain", "report_from"], name="idx_skew_report_domain_from"),
            models.Index(fields=["bk_biz_id", "report_from"], name="idx_skew_report_biz_from"),
        ]

    def __str__(self):
        return f"{self.cluster_domain}-{self.report_from}-{self.report_to}"
