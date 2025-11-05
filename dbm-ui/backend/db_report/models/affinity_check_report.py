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
from backend.db_report.report_basemodel import BaseReportABS


class AffinityCheckReport(BaseReportABS):
    cluster_id = models.IntegerField(default=0, help_text=_("集群ID"))
    cluster = models.CharField(max_length=255, default="", help_text=_("集群域名"))
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="", help_text=_("集群类型"))
    region = models.CharField(max_length=255, default="", help_text=_("地域"))
    affinity_type = models.CharField(max_length=255, default="", help_text=_("亲和性类型"))

    class Meta:
        indexes = [
            models.Index(fields=["cluster_id", "affinity_type", "create_at"]),
            models.Index(fields=["cluster_id"]),
        ]
