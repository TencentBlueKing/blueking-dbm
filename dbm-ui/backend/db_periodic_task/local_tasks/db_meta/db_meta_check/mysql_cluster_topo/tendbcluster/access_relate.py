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

from backend.db_meta.enums import InstanceInnerRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.decorator import checker_wrapper
from backend.db_report.enums import MetaCheckSubType


@checker_wrapper
def _cluster_spider_access_remote(c: Cluster) -> List[CheckResponse]:
    """
    master spider 只能访问 remote master
    slave spider 只能访问 remote slave
    mnt master spider 只能访问 remote master
    mnt slave spider 只能访问 remote slave
    """
    bad = []

    # 集群的主备实例数
    should_remote_master_cnt = 0
    should_remote_slave_cnt = 0
    for si in c.storageinstance_set.all():
        if si.instance_inner_role == InstanceInnerRole.MASTER:
            should_remote_master_cnt += 1
        elif si.instance_inner_role == InstanceInnerRole.SLAVE:
            should_remote_slave_cnt += 1

    for pi in c.proxyinstance_set.all():
        if pi.tendbclusterspiderext.spider_role in [
            TenDBClusterSpiderRole.SPIDER_MASTER,
            TenDBClusterSpiderRole.SPIDER_MNT,
        ]:
            can_access_remote_role = InstanceInnerRole.MASTER
        elif pi.tendbclusterspiderext.spider_role in [
            TenDBClusterSpiderRole.SPIDER_SLAVE,
            TenDBClusterSpiderRole.SPIDER_SLAVE_MNT,
        ]:
            can_access_remote_role = InstanceInnerRole.SLAVE
        else:
            continue

        right = []  # bind 关系正确的实例数
        for si in pi.storageinstance.all():
            if si.instance_inner_role != can_access_remote_role:
                bad.append(
                    CheckResponse(
                        msg=_(
                            "{} 关联到 {}: {}".format(
                                pi.tendbclusterspiderext.spider_role, si.instance_inner_role, si.ip_port
                            )
                        ),
                        check_subtype=MetaCheckSubType.ClusterTopo,
                        instance=pi,
                    )
                )
            else:
                right.append(si)

        # spider_master bind remote_master 数量和集群 remote_master 数量不一致
        if (
            pi.tendbclusterspiderext.spider_role == TenDBClusterSpiderRole.SPIDER_MASTER
            and len(right) != should_remote_master_cnt
        ):
            bad.append(
                CheckResponse(
                    msg=_(
                        "绑定的 REMOTE_MASTER 数量和集群 REMOTE_MASTER 数量不一致: {} != {}".format(
                            len(right), should_remote_master_cnt
                        )
                    ),
                    check_subtype=MetaCheckSubType.ClusterTopo,
                    instance=pi,
                )
            )
        # spider_slave bind remote_slave 数量和集群 remote_slave 数量不一致
        elif (
            pi.tendbclusterspiderext.spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE
            and len(right) != should_remote_slave_cnt
        ):
            bad.append(
                CheckResponse(
                    msg=_(
                        "绑定的 REMOTE_SLAVE 数量和集群 REMOTE_SLAVE 数量不一致: {} != {}".format(
                            len(right), should_remote_slave_cnt
                        )
                    ),
                    check_subtype=MetaCheckSubType.ClusterTopo,
                    instance=pi,
                )
            )

    return bad
