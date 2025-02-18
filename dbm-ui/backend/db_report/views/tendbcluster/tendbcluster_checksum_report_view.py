# -*- coding: utf-8 -*-
"""
tencentblueking is pleased to support the open source community by making 蓝鲸智云-db管理系统(blueking-bk-dbm) available.
copyright (c) 2017-2023 thl a29 limited, a tencent company. all rights reserved.
licensed under the mit license (the "license"); you may not use this file except in compliance with the license.
you may obtain a copy of the license at https://opensource.org/licenses/mit
unless required by applicable law or agreed to in writing, software distributed under the license is distributed on
an "as is" basis, without warranties or conditions of any kind, either express or implied. see the license for the
specific language governing permissions and limitations under the license.
"""
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_report.enums import ReportType
from backend.db_report.models import ChecksumCheckReport
from backend.db_report.register import register_report
from backend.db_report.views.checksum_check_report_view import ChecksumCheckReportBaseViewSet


@register_report(DBType.TenDBCluster)
class TendbClusterChecksumCheckReportViewSet(ChecksumCheckReportBaseViewSet):
    report_type = ReportType.CHECKSUM
    queryset = ChecksumCheckReport.objects.filter(cluster_type=ClusterType.TenDBCluster).order_by("-create_at")
