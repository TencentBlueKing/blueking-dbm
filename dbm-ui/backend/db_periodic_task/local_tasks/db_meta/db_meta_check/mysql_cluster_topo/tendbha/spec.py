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
from collections import defaultdict
from typing import List

from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import AccessLayer, ClusterType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, Machine
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.check_response import CheckResponse
from backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_topo.decorator import checker_wrapper
from backend.db_report.enums import MetaCheckSubType


@checker_wrapper
def cluster_machine_spec(c: Cluster) -> List[CheckResponse]:
    """
    集群规格
    """
    bad = []

    # 存储先只查 standby, 因为分组没设计
    storage_spec = defaultdict(list)
    for m in Machine.objects.filter(
        access_layer=AccessLayer.STORAGE, storageinstance__cluster=c, storageinstance__is_stand_by=True
    ):
        if m.spec_id <= 0:
            bad.append(CheckResponse(msg=_("规格为空"), check_subtype=MetaCheckSubType.MachineSpectEmpty, instance=m))
        else:
            storage_spec[m.spec_id].append(m.ip)

        if len(storage_spec) > 1:
            bad.append(
                CheckResponse(
                    msg=_("存储层存在多个规格 {}".format(list(storage_spec.keys()))),
                    check_subtype=MetaCheckSubType.MultiSpecInGroup,
                )
            )

    if c.cluster_type == ClusterType.TenDBHA:
        proxy_spec = defaultdict(list)
        for m in Machine.objects.filter(access_layer=AccessLayer.PROXY, proxyinstance__cluster=c):
            if m.spec_id <= 0:
                bad.append(CheckResponse(msg=_("规格为空"), check_subtype=MetaCheckSubType.MachineSpectEmpty, instance=m))
            else:
                proxy_spec[m.spec_id].append(m.ip)

        if len(proxy_spec) > 1:
            bad.append(
                CheckResponse(
                    msg=_("proxy 存在多个规格 {}".format(list(proxy_spec.keys()))),
                    check_subtype=MetaCheckSubType.MultiSpecInGroup,
                )
            )

    elif c.cluster_type == ClusterType.TenDBCluster:
        # spider 按角色查
        spider_master_spec = defaultdict(list)
        for m in Machine.objects.filter(
            access_layer=AccessLayer.PROXY,
            proxyinstance__cluster=c,
            proxyinstance__tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
        ):
            if m.spec_id <= 0:
                bad.append(CheckResponse(msg=_("规格为空"), check_subtype=MetaCheckSubType.MachineSpectEmpty, instance=m))
            else:
                spider_master_spec[m.spec_id].append(m.ip)

        if len(spider_master_spec) > 1:
            bad.append(
                CheckResponse(
                    msg=_("spider_master 存在多个规格 {}".format(list(spider_master_spec.keys()))),
                    check_subtype=MetaCheckSubType.MultiSpecInGroup,
                )
            )

        spider_slave_spec = defaultdict(list)
        for m in Machine.objects.filter(
            access_layer=AccessLayer.PROXY,
            proxyinstance__cluster=c,
            proxyinstance__tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE,
        ):
            if m.spec_id <= 0:
                bad.append(CheckResponse(msg=_("规格为空"), check_subtype=MetaCheckSubType.MachineSpectEmpty, instance=m))
            else:
                spider_slave_spec[m.spec_id].append(m.ip)

        if len(spider_slave_spec) > 1:
            bad.append(
                CheckResponse(
                    msg=_("spider_slave 存在多个规格 {}".format(list(spider_slave_spec.keys()))),
                    check_subtype=MetaCheckSubType.MultiSpecInGroup,
                )
            )
    else:
        pass

    return bad
