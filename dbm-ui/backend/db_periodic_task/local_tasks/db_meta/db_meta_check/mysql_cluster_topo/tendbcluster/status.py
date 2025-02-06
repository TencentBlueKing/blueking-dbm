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

from backend.db_meta.enums import InstanceInnerRole, InstancePhase, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.decorator import checker_wrapper
from backend.db_report.enums import MetaCheckSubType


@checker_wrapper
def _cluster_master_spider_count(c: Cluster) -> List[CheckResponse]:
    """
    至少 2 个存活的 master spider
    """
    cnt = 0
    for pi in c.proxyinstance_set.all():
        if (
            pi.status == InstanceStatus.RUNNING
            and pi.phase == InstancePhase.ONLINE
            and pi.tendbclusterspiderext.spider_role == TenDBClusterSpiderRole.SPIDER_MASTER
        ):
            cnt += 1

    bad = []
    if cnt < 2:
        bad.append(CheckResponse(msg=_("正常 spider master 不足 2 个"), check_subtype=MetaCheckSubType.ClusterTopo))

    return bad


@checker_wrapper
def _cluster_master_remote_count(c: Cluster) -> List[CheckResponse]:
    """
    master remote 数量等于分片数
    """
    bad = []

    remote_master_count = 0
    for si in c.storageinstance_set.all():
        if si.instance_inner_role == InstanceInnerRole.MASTER:
            remote_master_count += 1

    shard_count = c.tendbclusterstorageset_set.count()
    if shard_count != remote_master_count:
        bad.append(
            CheckResponse(
                msg=_("分片数 {} != remote master 数 {}".format(shard_count, remote_master_count)),
                check_subtype=MetaCheckSubType.ClusterTopo,
            )
        )

    return bad


@checker_wrapper
def _cluster_one_standby_slave_each_shard(c: Cluster) -> List[CheckResponse]:
    """
    每个 shard 的 standby slave 是唯一的
    """
    bad = []

    for si in c.storageinstance_set.all():
        if si.instance_inner_role == InstanceInnerRole.MASTER:
            m = []
            for tp in si.as_ejector.all():
                if tp.receiver.is_stand_by:
                    m.append(tp.receiver)

            if len(m) <= 0:
                bad.append(
                    CheckResponse(
                        msg=_("无 standby slave"),
                        check_subtype=MetaCheckSubType.ClusterTopo,
                        instance=si,
                    )
                )

            if len(m) > 1:
                bad.append(
                    CheckResponse(
                        msg=_("standby slave 多余 1 个: {}".format(",".join([ele.ip_port for ele in m]))),
                        check_subtype=MetaCheckSubType.ClusterTopo,
                        instance=si,
                    )
                )

    return bad
