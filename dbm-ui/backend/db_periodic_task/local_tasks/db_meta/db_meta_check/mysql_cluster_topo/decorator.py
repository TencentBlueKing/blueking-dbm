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
from typing import List

from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_report.models import MetaCheckReport


def checker_wrapper(checker):
    def wrapper(c: Cluster) -> List[MetaCheckReport]:
        out_reports = []
        check_response: List[CheckResponse] = checker(c)
        if not check_response:
            return out_reports

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
                ip="0.0.0.0",
                port=0,
                machine_type="",
            )
            if cr.instance:
                out_report.ip = cr.instance.machine.ip
                out_report.port = cr.instance.port
                out_report.machine_type = cr.instance.machine_type

            out_reports.append(out_report)

        return out_reports

    return wrapper
