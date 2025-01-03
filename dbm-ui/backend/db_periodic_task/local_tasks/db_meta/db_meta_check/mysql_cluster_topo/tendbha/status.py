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

from backend.db_meta.enums import ClusterEntryRole, ClusterStatus, InstanceInnerRole, InstancePhase, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.decorator import checker_wrapper
from backend.db_report.enums import MetaCheckSubType


@checker_wrapper
def _cluster_status(c: Cluster) -> List[CheckResponse]:
    if c.status != ClusterStatus.NORMAL:
        return [
            CheckResponse(
                msg=_("集群状态异常: {}".format(c.status)),
                check_subtype=MetaCheckSubType.ClusterTopo,
            )
        ]


@checker_wrapper
def _cluster_instance_status(c: Cluster) -> List[CheckResponse]:
    bad = []
    for si in c.storageinstance_set.all():
        if si.status != InstanceStatus.RUNNING or si.phase != InstancePhase.ONLINE:
            bad.append(
                CheckResponse(
                    msg=_("实例 {} 状态异常: {}, {}".format(si.ip_port, si.status, si.phase)),
                    check_subtype=MetaCheckSubType.ClusterTopo,
                    instance=si,
                )
            )

    for pi in c.proxyinstance_set.all():
        if pi.status != InstanceStatus.RUNNING or pi.phase != InstancePhase.ONLINE:
            bad.append(
                CheckResponse(
                    msg=_("实例 {} 状态异常: {}, {}".format(pi.ip_port, pi.status, pi.phase)),
                    check_subtype=MetaCheckSubType.ClusterTopo,
                    instance=pi,
                )
            )

    return bad


@checker_wrapper
def _cluster_master_entry_count(c: Cluster) -> List[CheckResponse]:
    """
    至少 1 个主访问入口
    """
    cnt = 0
    for ce in c.clusterentry_set.all():
        if ce.role == ClusterEntryRole.MASTER_ENTRY:
            cnt += 1

    if cnt <= 0:
        return [CheckResponse(msg=_("缺少主访问入口"), check_subtype=MetaCheckSubType.ClusterTopo)]


@checker_wrapper
def _cluster_proxy_count(c: Cluster) -> List[CheckResponse]:
    """
    至少 2 个存活的 proxy
    """
    cnt = 0
    for pi in c.proxyinstance_set.all():
        if pi.status == InstanceStatus.RUNNING and pi.phase == InstancePhase.ONLINE:
            cnt += 1

    if cnt < 2:
        return [CheckResponse(msg=_("正常 proxy 不足 2 个"), check_subtype=MetaCheckSubType.ClusterTopo)]


@checker_wrapper
def _cluster_one_master(c: Cluster) -> List[CheckResponse]:
    """只能有一个 master"""
    m = []
    for si in c.storageinstance_set.all():
        if si.instance_inner_role == InstanceInnerRole.MASTER:
            m.append(si)

    if len(m) <= 0:
        return [CheckResponse(msg=_("无 master 实例"), check_subtype=MetaCheckSubType.ClusterTopo)]

    if len(m) > 1:
        return [
            CheckResponse(
                msg=_("master 多余 1 个: {}".format(",".join([ele.ip_port for ele in m]))),
                check_subtype=MetaCheckSubType.ClusterTopo,
            )
        ]


@checker_wrapper
def _cluster_master_status(
    c: Cluster,
) -> List[CheckResponse]:
    """
    master 必须
    status == running
    phase == online
    is_stand_by = True
    """
    cnt = 0
    for si in c.storageinstance_set.all():
        if (
            si.instance_inner_role == InstanceInnerRole.MASTER
            and si.status == InstanceStatus.RUNNING
            and si.phase == InstancePhase.ONLINE
        ):
            cnt += 1

    if cnt <= 0:
        return [CheckResponse(msg=_("无正常 master"), check_subtype=MetaCheckSubType.ClusterTopo)]


@checker_wrapper
def _cluster_one_standby_slave(
    c: Cluster,
) -> List[CheckResponse]:
    """
    只能有一个 standby slave
    """
    m = []
    for si in c.storageinstance_set.all():
        if si.instance_inner_role == InstanceInnerRole.SLAVE and si.is_stand_by is True:
            m.append(si)

    if len(m) <= 0:
        return [CheckResponse(msg=_("无 standby slave"), check_subtype=MetaCheckSubType.ClusterTopo)]

    if len(m) > 1:
        return [
            CheckResponse(
                msg=_("standby slave 多余 1 个: {}".format(",".join([ele.ip_port for ele in m]))),
                check_subtype=MetaCheckSubType.ClusterTopo,
            )
        ]


@checker_wrapper
def _cluster_standby_slave_status(c: Cluster) -> List[CheckResponse]:
    """
    standby slave 必须正常
    """
    bad = []
    for si in c.storageinstance_set.all():
        if (si.instance_inner_role == InstanceInnerRole.SLAVE and si.is_stand_by is True) and (
            si.status != InstanceStatus.RUNNING or si.phase != InstancePhase.ONLINE
        ):
            bad.append(
                CheckResponse(
                    msg=_("standby slave {} 状态异常: {}, {}".format(si.ip_port, si.status, si.phase)),
                    check_subtype=MetaCheckSubType.ClusterTopo,
                    instance=si,
                )
            )

    return bad
