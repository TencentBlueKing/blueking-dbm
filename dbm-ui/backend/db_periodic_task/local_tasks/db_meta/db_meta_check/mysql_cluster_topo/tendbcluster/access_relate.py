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

    return bad
