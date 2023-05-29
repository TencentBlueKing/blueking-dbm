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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster


def biz_clusters(bk_biz_id: int, immute_domains: Optional[List[str]]):

    res = []

    qs = Cluster.objects.prefetch_related("storageinstance_set", "storageinstance_set__machine",).filter(
        bk_biz_id=bk_biz_id,
        cluster_type=ClusterType.TenDBSingle.value,
    )

    if immute_domains:
        qs = qs.filter(immute_domain__in=immute_domains)

    for cluster in qs:
        storage_instance = cluster.storageinstance_set.first()
        res.append(
            {
                "immute_domain": cluster.immute_domain,
                "cluster_type": cluster.cluster_type,
                "bk_biz_id": bk_biz_id,
                "db_module_id": cluster.db_module_id,
                "bk_cloud_id": cluster.bk_cloud_id,
                "storage": {
                    "ip": storage_instance.machine.ip,
                    "port": storage_instance.port,
                    "instance_inner_role": storage_instance.instance_inner_role,
                    "instance_role": storage_instance.instance_role,
                    "bk_cloud_id": storage_instance.machine.bk_cloud_id,
                    "status": storage_instance.status,
                    "bk_instance_id": storage_instance.bk_instance_id,
                },
            }
        )

    return res
