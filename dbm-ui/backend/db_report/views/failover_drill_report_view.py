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
from rest_framework import serializers, status

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_report.enums import DrillFilterType, ReportFieldFormat, ReportType
from backend.db_report.models import FailoverDrillReport
from backend.db_report.report_baseview import BaseDrillReportViewSet
from backend.db_report.serializers import ReportCommonFieldSerializerMixin
from backend.db_services.redis.autofix.enums import DBHASwitchResult

logger = logging.getLogger("root")

SWAGGER_TAG = _("演练报告")


class FailoverDrillSerializer(serializers.ModelSerializer, ReportCommonFieldSerializerMixin):
    class Meta:
        model = FailoverDrillReport
        fields = (
            "city",
            "cluster_domain",
            "cluster_type",
            "instance_type",
            "state",
            "trigger_dbha_time",
            "switch_start_time",
            "switch_finished_time",
            "dbha_status",
            "dbha_info",
        )


class FailoverDrillReportViewSet(BaseDrillReportViewSet):
    """切换演练报告视图"""

    queryset = FailoverDrillReport.objects.all()
    serializer_class = FailoverDrillSerializer

    filter_fields = {
        "city": ["exact", "in"],
        "cluster_domain": ["exact", "in"],
        "cluster_type": ["exact", "in"],
        "instance_type": ["exact", "in"],
        "state": ["exact", "in"],
        "dbha_status": ["exact", "in"],
        "create_at": ["gte", "lte"],
    }
    ordering_fields = ["trigger_dbha_time", "switch_start_time", "switch_finished_time"]

    report_type = ReportType.FAIL_OVER_DRILL.value
    report_title = [
        {
            "name": "city",
            "display_name": _("城市"),
            "format": ReportFieldFormat.TEXT.value,
            "filter": {"type": DrillFilterType.TEXT},
        },
        {
            "name": "cluster_type",
            "display_name": _("架构类型"),
            "format": ReportFieldFormat.TEXT.value,
            # 枚举类别在子类声明
            "filter": {"type": DrillFilterType.TEXT},
        },
        {
            "name": "instance_type",
            "display_name": _("实例角色"),
            "format": ReportFieldFormat.TEXT.value,
            "filter": {"type": DrillFilterType.TEXT},
        },
        {
            "name": "cluster_domain",
            "display_name": _("域名"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "state",
            "display_name": _("状态"),
            "format": ReportFieldFormat.STATUS.value,
        },
        {
            "name": "trigger_dbha_time",
            "display_name": _("触发 DBHA 时间"),
            "format": ReportFieldFormat.TIME.value,
            "ordering": True,
        },
        {
            "name": "switch_start_time",
            "display_name": _("DBHA 切换开始时间"),
            "format": ReportFieldFormat.TIME.value,
            "ordering": True,
        },
        {
            "name": "switch_finished_time",
            "display_name": _("DBHA 切换完成时间"),
            "format": ReportFieldFormat.TIME.value,
            "ordering": True,
        },
        {
            "name": "dbha_status",
            "display_name": _("DBHA 切换状态"),
            "format": ReportFieldFormat.TEXT.value,
            "filter": {
                "type": DrillFilterType.ENUM,
                "enums": [{"value": item[0], "label": item[1]} for item in DBHASwitchResult.get_choices()],
            },
        },
        {
            "name": "dbha_info",
            "display_name": _("DBHA 切换信息"),
            "format": ReportFieldFormat.LOG.value,
        },
    ]

    @common_swagger_auto_schema(
        operation_summary=_("切换演练报告"),
        responses={status.HTTP_200_OK: FailoverDrillSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
