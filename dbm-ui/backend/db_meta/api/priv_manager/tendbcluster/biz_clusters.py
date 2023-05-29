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
from typing import List, Optional

from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster


def biz_clusters(bk_biz_id: int, immute_domains: Optional[List[str]]):
    res = []

    qs = Cluster.objects.prefetch_related("proxyinstance_set", "proxyinstance_set__machine").filter(
        bk_biz_id=bk_biz_id,
        cluster_type=ClusterType.TenDBCluster.value,
    )

    if immute_domains:
        qs = qs.filter(immute_domain__in=immute_domains)

    for cluster in qs:

        res.append(
            {
                "immute_domain": cluster.immute_domain,
                "cluster_type": cluster.cluster_type,
                "bk_biz_id": bk_biz_id,
                "db_module_id": cluster.db_module_id,
                "bk_cloud_id": cluster.bk_cloud_id,
                "spider_master": [
                    {
                        "ip": ele.machine.ip,
                        "port": ele.port,
                        "bk_instance_id": ele.bk_instance_id,
                        "bk_cloud_id": ele.machine.bk_cloud_id,
                    }
                    for ele in cluster.proxyinstance_set.filter(
                        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value
                    )
                ],
                "spider_slave": [
                    {
                        "ip": ele.machine.ip,
                        "port": ele.port,
                        "bk_instance_id": ele.bk_instance_id,
                        "bk_cloud_id": ele.machine.bk_cloud_id,
                    }
                    for ele in cluster.proxyinstance_set.filter(
                        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value
                    )
                ],
                "spider_mnt": [
                    {
                        "ip": ele.machine.ip,
                        "port": ele.port,
                        "bk_instance_id": ele.bk_instance_id,
                        "bk_cloud_id": ele.machine.bk_cloud_id,
                    }
                    for ele in cluster.proxyinstance_set.filter(
                        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MNT.value
                    )
                ],
            }
        )

    return res
