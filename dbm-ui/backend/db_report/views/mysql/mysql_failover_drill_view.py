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
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_report.enums import ReportFieldFormat, ReportStateType
from backend.db_report.models import FailoverDrillReport
from backend.db_report.register import register_drill_report
from backend.db_report.views.failover_drill_report_view import FailoverDrillReportViewSet, FailoverDrillSerializer

logger = logging.getLogger("root")

TRIGGER_DBHA_TIMEOUT = 70


MYSQL_CUSTOM_FIELDS = [
    {
        "name": "duration",
        "display_name": _("切换恢复耗时(秒)"),
        "format": ReportFieldFormat.TEXT.value,
        "ordering": True,
    },
    {
        "name": "dbha_health_status",
        "display_name": _("DBHA 健康状态"),
        "format": ReportFieldFormat.STATUS.value,
        "ordering": True,
    },
]


class MySQLFailoverDrillSerializer(FailoverDrillSerializer):

    duration = serializers.SerializerMethodField(help_text=_("触发dbha到切换完成耗时"))
    dbha_health_status = serializers.SerializerMethodField(help_text=_("dbha健康状态"))

    def get_duration(self, obj):
        if obj.trigger_dbha_time and obj.switch_finished_time:
            logger.info(_("type: obj({}), time({})").format(type(obj), type(obj.trigger_dbha_time)))
            return round((obj.switch_finished_time - obj.trigger_dbha_time).total_seconds(), 2)
        return 0

    def get_dbha_health_status(self, obj):
        # 触发dbha超时时间阈值为70秒
        if self.get_duration(obj) > TRIGGER_DBHA_TIMEOUT:
            return ReportStateType.ABNORMAL.value

        if self.get_duration(obj) == 0:
            return ReportStateType.WARNING.value

        return ReportStateType.NORMAL.value

    class Meta(FailoverDrillSerializer.Meta):
        fields = (
            "city",
            "cluster_domain",
            "cluster_type",
            "instance_type",
            "state",
            "create_at",
            "trigger_dbha_time",
            "switch_start_time",
            "switch_finished_time",
            "dbha_status",
            "duration",  # MySQL-specific
            "dbha_health_status",  # MySQL-specific
            "dbha_info",
        )


@register_drill_report(DBType.MySQL)
class MySQLFailoverDrillReportViewSet(FailoverDrillReportViewSet):
    cluster_types = [ClusterType.TenDBSingle, ClusterType.TenDBHA]
    queryset = FailoverDrillReport.objects.filter(cluster_type__in=cluster_types)
    serializer_class = MySQLFailoverDrillSerializer
    report_title = list(FailoverDrillReportViewSet.report_title)
    report_title[-1:-1] = MYSQL_CUSTOM_FIELDS


@register_drill_report(DBType.TenDBCluster)
class TendbClusterFailoverDrillReportViewSet(FailoverDrillReportViewSet):
    cluster_types = [ClusterType.TenDBCluster]
    queryset = FailoverDrillReport.objects.filter(cluster_type__in=cluster_types)
    serializer_class = MySQLFailoverDrillSerializer
    report_title = list(FailoverDrillReportViewSet.report_title)
    report_title[-1:-1] = MYSQL_CUSTOM_FIELDS
