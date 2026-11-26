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

from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, InstancePhase, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.decorator import checker_wrapper
from backend.db_report.enums import MetaCheckSubType


@checker_wrapper
def _cluster_master_entry_on_proxy(c: Cluster) -> List[CheckResponse]:
    """
    主入口 bind 到 proxy 的数量必须和集群正常 proxy 相等
    """
    bad = []
    for cme in c.clusterentry_set.filter(forward_to__isnull=True, cluster_entry_type=ClusterEntryType.DNS):
        if cme.role == ClusterEntryRole.MASTER_ENTRY:
            cluster_proxy_cnt = 0
            for pi in c.proxyinstance_set.all():
                if pi.status == InstanceStatus.RUNNING and pi.phase == InstancePhase.ONLINE:
                    cluster_proxy_cnt += 1

            if cme.proxyinstance_set.count() != cluster_proxy_cnt:
                bad.append(
                    CheckResponse(
                        msg=_("主访问入口 {} 关联 proxy 和集群 proxy 数量不相等".format(cme.entry)),
                        check_subtype=MetaCheckSubType.TenDBHAProxyCountNotMatch,
                    )
                )

    return bad


@checker_wrapper
def _cluster_master_entry_on_storage(c: Cluster) -> List[CheckResponse]:
    """
    主入口不能 bind 到存储
    """
    bad = []
    for cme in c.clusterentry_set.filter(forward_to__isnull=True):
        if cme.role == ClusterEntryRole.MASTER_ENTRY:
            for si in cme.storageinstance_set.all():
                bad.append(
                    CheckResponse(
                        msg=_("主访问入口 {} 关联到存储实例".format(cme.entry)),
                        check_subtype=MetaCheckSubType.TenDBHAMasterEntryBindStorage,
                        instance=si,
                    )
                )

    return bad
