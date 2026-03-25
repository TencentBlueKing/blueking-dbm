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

from backend.db_report import mock_data
from backend.db_report.enums import ReportFieldFormat
from backend.db_report.models.redis_check_report import RedisCheckReport
from backend.db_report.report_baseview import ReportBaseViewSet

logger = logging.getLogger("root")


class RedisCheckReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedisCheckReport
        fields = (
            "bk_biz_id",
            "cluster",
            "cluster_type",
            "shard",
            "instance",
            "subtype",
            "msg",
            "create_at",
            "failed_days",
            "state",
        )
        swagger_schema_fields = {"example": mock_data.REDIS_EXPORTER_CHECK_DATA}


class RedisCheckReportBaseViewSet(ReportBaseViewSet):
    queryset = RedisCheckReport.objects.all()
    serializer_class = RedisCheckReportSerializer
    report_title = [
        {
            "name": "bk_biz_id",
            "display_name": _("业务"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "cluster",
            "display_name": _("集群域名"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "cluster_type",
            "display_name": _("集群类型"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "state",
            "display_name": _("检查结果"),
            "format": ReportFieldFormat.STATUS.value,
        },
        {
            "name": "shard",
            "display_name": _("节点类型"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "msg",
            "display_name": _("详情"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "create_at",
            "display_name": _("巡检时间"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "failed_days",
            "display_name": _("持续天数"),
            "format": ReportFieldFormat.TEXT.value,
        },
    ]
