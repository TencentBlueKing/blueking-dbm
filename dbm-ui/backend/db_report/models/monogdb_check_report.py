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


class MongodbBackupCheckReport(BaseReportABS):
    cluster_id = models.IntegerField(default=0, verbose_name=_("集群 id"))
    cluster = models.CharField(max_length=255, default="")
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    shard = models.CharField(max_length=100, verbose_name=_("shard or set_name"))
    instance = models.CharField(max_length=100, verbose_name=_("实例节点 ip:port"))
    subtype = models.CharField(max_length=100, verbose_name=_("检查子项"))  # full_backup, exporter
    report_day = models.IntegerField(default=0, verbose_name=_("报告日期"))

    class Meta:
        indexes = [
            models.Index(fields=["bk_biz_id", "create_at"]),
            models.Index(fields=["status", "create_at"]),
            models.Index(fields=["creator", "create_at"]),
            models.Index(fields=["cluster", "create_at"]),
            models.Index(fields=["subtype", "report_day", "cluster_id"]),
            models.Index(fields=["subtype", "bk_biz_id", "state", "create_at"]),
        ]
