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
from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, MachineType
from backend.db_meta.models import Cluster
from backend.db_report.enums import MetaCheckSubType
from backend.db_report.models import MetaCheckReport


def check_cluster_topo():
    _check_tendbsingle_topo()
    _check_tendbha_topo()
    _check_tendbcluster_topo()


def _check_tendbsingle_topo():
    """
    有且只有一个存储实例
    """
    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBSingle):
        messages = []
        if c.proxyinstance_set.exists():
            messages.append(_("有 {} 个接入层实例".format(c.proxyinstance_set.count())))

        if c.storageinstance_set.count() != 1:
            messages.append(_("有 {} 个存储层实例".format(c.storageinstance_set.count())))

        ins = c.storageinstance_set.get()
        if not (
            ins.machine.machine_type == MachineType.SINGLE.value
            and ins.instance_role == InstanceRole.ORPHAN.value
            and ins.instance_inner_role == InstanceInnerRole.ORPHAN.value
        ):
            messages.append(
                _(
                    "实例 {} ({}-{}-{}) 与集群类型不匹配".format(
                        ins.ip_port, ins.machine.machine_type, ins.instance_role, ins.instance_inner_role
                    )
                )
            )

        if messages:
            MetaCheckReport.objects.create(
                bk_biz_id=c.bk_biz_id,
                bk_cloud_id=c.bk_cloud_id,
                cluster=c.immute_domain,
                cluster_type=ClusterType.TenDBSingle,
                status=False,
                msg=", ".join(messages),
                subtype=MetaCheckSubType.ClusterTopo.value,
            )


def _check_tendbha_topo():
    """
    1. 至少 2 个 proxy
    2. 1 个 master
    3. 至少 1 个 slave
    """
    Cluster.objects.filter(cluster_type=ClusterType.TenDBHA)


def _check_tendbcluster_topo():
    Cluster.objects.filter(cluster_type=ClusterType.TenDBCluster)
