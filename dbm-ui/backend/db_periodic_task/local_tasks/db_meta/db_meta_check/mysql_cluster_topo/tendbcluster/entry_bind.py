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

from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import ClusterEntryRole, InstancePhase, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.decorator import checker_wrapper
from backend.db_report.enums import MetaCheckSubType


@checker_wrapper
def _cluster_entry_on_spider(c: Cluster) -> List[CheckResponse]:
    """
    访问入口 bind 到 spider 的数量必须和集群正常 spider 相等
    """
    bad = []
    for ce in c.clusterentry_set.all():

        if ce.role == ClusterEntryRole.MASTER_ENTRY:
            spider_role = TenDBClusterSpiderRole.SPIDER_MASTER
        else:
            spider_role = TenDBClusterSpiderRole.SPIDER_SLAVE

        cnt = 0
        for pi in c.proxyinstance_set.all():
            if (
                pi.status == InstanceStatus.RUNNING
                and pi.phase == InstancePhase.ONLINE
                and pi.tendbclusterspiderext.spider_role == spider_role
            ):
                cnt += 1

        if cnt != ce.proxyinstance_set.count():
            bad.append(
                CheckResponse(
                    msg=_("访问入口 {} 关联 {} 和集群 {} 数量不相等".format(ce.entry, spider_role, spider_role)),
                    check_subtype=MetaCheckSubType.ClusterTopo,
                )
            )

    return bad


@checker_wrapper
def _cluster_entry_on_storage(c: Cluster) -> List[CheckResponse]:
    """
    访问入口不能 bind 到存储
    """
    bad = []
    for ce in c.clusterentry_set.all():
        for si in ce.storageinstance_set.all():
            bad.append(
                CheckResponse(
                    msg=_("访问入口 {} 关联到存储实例".format(ce.entry)), check_subtype=MetaCheckSubType.ClusterTopo, instance=si
                )
            )

    return bad
