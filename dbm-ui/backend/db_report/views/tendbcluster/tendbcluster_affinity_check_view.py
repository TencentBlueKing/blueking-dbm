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

from django.utils.translation import gettext as _
from rest_framework import status

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_report.enums import SWAGGER_TAG, ReportType
from backend.db_report.models import AffinityCheckReport
from backend.db_report.register import register_report
from backend.db_report.views.mysql.mysql_affinity_check_view import (
    MySQLAffinityCheckReportBaseViewSet,
    MySQLAffinityCheckReportSerializer,
)


@register_report(DBType.TenDBCluster)
class TendbClusterAffinityCheckReportViewSet(MySQLAffinityCheckReportBaseViewSet):
    """TenDBCluster 集群亲和性检查报告"""

    queryset = AffinityCheckReport.objects.filter(cluster_type=ClusterType.TenDBCluster.value).order_by("-create_at")
    report_type = ReportType.AFFINITY_CHECK

    @common_swagger_auto_schema(
        operation_summary=_("TenDBCluster 亲和性检查"),
        responses={status.HTTP_200_OK: MySQLAffinityCheckReportSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
