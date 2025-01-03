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

from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.decorator import checker_wrapper
from backend.db_report.enums import MetaCheckSubType


@checker_wrapper
def _cluster_master_as_ejector(c: Cluster) -> List[CheckResponse]:
    """
    master 只能是 ejector
    """
    bad = []
    for si in c.storageinstance_set.all():
        if si.instance_inner_role == InstanceInnerRole.MASTER:
            for tp in si.as_receiver.all():
                bad.append(
                    CheckResponse(
                        msg=_("master 为 receiver 与 {} 有同步关系".format(tp.ejector.ip_port)),
                        check_subtype=MetaCheckSubType.ClusterTopo,
                        instance=si,
                    )
                )

    return bad


@checker_wrapper
def _cluster_slave_as_receiver(c: Cluster) -> List[CheckResponse]:
    """
    slave 只能是 receiver
    """
    bad = []
    for si in c.storageinstance_set.all():
        if si.instance_inner_role == InstanceInnerRole.SLAVE:
            for tp in si.as_ejector.all():
                bad.append(
                    CheckResponse(
                        msg=_("slave 作为 ejector 与 {} 有同步关系".format(tp.receiver.ip_port)),
                        check_subtype=MetaCheckSubType.ClusterTopo,
                        instance=si,
                    )
                )

    return bad


@checker_wrapper
def _cluster_replicate_out(c: Cluster) -> List[CheckResponse]:
    """
    不能同步到集群外部
    """
    bad = []
    for si in c.storageinstance_set.all():
        for tp in si.as_ejector.all():
            for rc in tp.receiver.cluster.all():
                if rc.id != c.id:
                    bad.append(
                        CheckResponse(
                            msg=_("与外部集群 {} {} 有同步关系".format(rc.immute_domain, tp.receiver.ip_port)),
                            check_subtype=MetaCheckSubType.ClusterTopo,
                            instance=si,
                        )
                    )

        for tp in si.as_receiver.all():
            for rc in tp.ejector.cluster.all():
                if rc.id != c.id:
                    bad.append(
                        CheckResponse(
                            msg=_("与外部集群 {} {} 有同步关系".format(rc.immute_domain, tp.receiver.ip_port)),
                            check_subtype=MetaCheckSubType.ClusterTopo,
                            instance=si,
                        )
                    )

    return bad
