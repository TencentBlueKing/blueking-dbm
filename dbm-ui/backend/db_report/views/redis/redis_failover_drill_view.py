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

import logging

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_report.enums import ReportFieldFormat
from backend.db_report.models import FailoverDrillReport
from backend.db_report.register import register_drill_report
from backend.db_report.views.failover_drill_report_view import FailoverDrillReportViewSet, FailoverDrillSerializer

logger = logging.getLogger("root")

REDIS_CUSTOM_FIELDS = [
    {
        "name": "task_info",
        "display_name": _("任务信息"),
        "format": ReportFieldFormat.LOG.value,
    },
]


class RedisFailoverDrillSerializer(FailoverDrillSerializer):
    class Meta(FailoverDrillSerializer.Meta):
        fields = FailoverDrillSerializer.Meta.fields + ("task_info",)


@register_drill_report(DBType.Redis)
class RedisFailoverDrillReportViewSet(FailoverDrillReportViewSet):
    cluster_types = ClusterType.redis_cluster_types()
    queryset = FailoverDrillReport.objects.filter(cluster_type__in=cluster_types)
    serializer_class = RedisFailoverDrillSerializer
    filter_fields = {
        "city": ["exact", "in"],
        "cluster_domain": ["exact", "in"],
        "cluster_type": ["exact", "in"],
        "instance_type": ["exact", "in"],
        "state": ["exact", "in"],
        "dbha_status": ["exact", "in"],
        "create_at": ["gte", "lte"],
    }
    report_title = FailoverDrillReportViewSet.report_title + REDIS_CUSTOM_FIELDS
