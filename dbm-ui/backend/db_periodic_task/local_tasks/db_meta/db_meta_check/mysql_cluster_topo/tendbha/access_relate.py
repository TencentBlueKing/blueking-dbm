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
def _cluster_proxy_access_master(
    c: Cluster,
) -> List[CheckResponse]:
    """
    proxy 必须且只能关联到 master
    """
    bad = []
    for pi in c.proxyinstance_set.all():
        for si in pi.storageinstance.all():
            if si.instance_inner_role != InstanceInnerRole.MASTER:
                bad.append(
                    CheckResponse(
                        msg=_("proxy 关联到 {}: {}".format(si.instance_inner_role, si.ip_port)),
                        check_subtype=MetaCheckSubType.ClusterTopo,
                        instance=pi,
                    )
                )

    return bad
