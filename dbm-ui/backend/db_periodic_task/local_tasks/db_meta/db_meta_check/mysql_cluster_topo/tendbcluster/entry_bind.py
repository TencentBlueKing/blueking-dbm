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

from backend.db_meta.enums import (
    ClusterEntryRole,
    ClusterEntryType,
    InstancePhase,
    InstanceStatus,
    TenDBClusterSpiderRole,
)
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.clb_entry_bind_check import (
    TENDBCLUSTER_CLB_SUBTYPES,
    collect_clb_entry_check_results,
)
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.decorator import checker_wrapper
from backend.db_report.enums import MetaCheckSubType


@checker_wrapper
def _cluster_entry_on_spider(c: Cluster) -> List[CheckResponse]:
    """
    访问入口 bind 到 spider 的数量必须和集群正常 spider 相等
    """
    bad = []
    for ce in c.clusterentry_set.filter(forward_to__isnull=True, cluster_entry_type=ClusterEntryType.DNS):

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
                    check_subtype=MetaCheckSubType.TenDBClusterSpiderCountNotMatch,
                )
            )

    return bad


@checker_wrapper
def _cluster_clb_exists_and_rs_match(c: Cluster) -> List[CheckResponse]:
    """
    存在 CLB 入口时：校验名字服务可查询该 CLB，且后端 RS 与当前 CLB entry 的 proxy 元数据一致。

    主/从若各一条 CLB：Master 入口 CLB 只绑 Spider Master 代理，Slave 入口 CLB 只绑 Spider Slave；
    元数据上体现为各自 ClusterEntry.proxyinstance_set，与 db_meta CLB create_by_role 写入一致。
    RS 与名字服务 data.ips 返回字符串集合及本条 entry 代理 ip:port 拼接字符串集合对比（strip 后）。
    """
    return collect_clb_entry_check_results(c, TENDBCLUSTER_CLB_SUBTYPES)


@checker_wrapper
def _cluster_entry_on_storage(c: Cluster) -> List[CheckResponse]:
    """
    访问入口不能 bind 到存储
    """
    bad = []
    for ce in c.clusterentry_set.filter(forward_to__isnull=True):
        for si in ce.storageinstance_set.all():
            bad.append(
                CheckResponse(
                    msg=_("访问入口 {} 关联到存储实例".format(ce.entry)),
                    check_subtype=MetaCheckSubType.TenDBClusterEntryBindStorage,
                    instance=si,
                )
            )

    return bad
