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
import datetime
from datetime import timedelta
from typing import List

from django.db.models import Q

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_report.enums import ReportStateType
from backend.db_report.models import MetaCheckReport


def checker_wrapper(checker):
    def wrapper(c: Cluster) -> List[MetaCheckReport]:
        out_reports = []
        check_response: List[CheckResponse] = checker(c)
        if not check_response:
            return out_reports

        create_18h_ago = datetime.datetime.now() - timedelta(hours=18)
        create_25h_ago = datetime.datetime.now() - timedelta(hours=25)
        for cr in check_response:
            out_report = MetaCheckReport(
                subtype=cr.check_subtype,
                bk_biz_id=c.bk_biz_id,
                bk_cloud_id=c.bk_cloud_id,
                status=False,
                msg=cr.msg,
                cluster=c.immute_domain,
                cluster_type=c.cluster_type,
                creator="system",
                updater="system",
                # create_at=timezone.localtime(timezone.now()),
                # update_at=timezone.localtime(timezone.now()),
                ip="",
                port=0,
                machine_type="",
                state=ReportStateType.ABNORMAL.value,
            )
            if cr.instance:
                out_report.ip = cr.instance.machine.ip
                out_report.port = cr.instance.port
                out_report.machine_type = cr.instance.machine_type

            if out_report.cluster_type in [
                ClusterType.TenDBSingle,
                ClusterType.TenDBHA,
                ClusterType.TenDBCluster,
                ClusterType.SqlserverHA,
                ClusterType.SqlserverSingle,
            ]:
                query = Q(
                    cluster=out_report.cluster,
                    subtype=out_report.subtype,
                    create_at__gte=create_25h_ago,
                    create_at__lte=create_18h_ago,
                )
                if cr.instance:
                    query &= Q(ip=out_report.ip, port=out_report.port)
                else:
                    # 如果Instance是空，过滤时候做空过滤处理，避免读取数据失败
                    query &= Q(ip__isnull=True, port=0)

                last_row = MetaCheckReport.objects.filter(query).order_by("-create_at")
                if last_row.exists():
                    out_report.failed_days = last_row.first().failed_days + 1

            out_reports.append(out_report)

        return out_reports

    return wrapper
