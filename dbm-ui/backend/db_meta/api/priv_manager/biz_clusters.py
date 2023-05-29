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

from django.db.models import F

from backend.db_meta.models import Cluster


def biz_clusters(bk_biz_id: int, immute_domains: Optional[List[str]]):
    res = []

    qs = Cluster.objects.prefetch_related(
        "storageinstance_set", "proxyinstance_set", "storageinstance_set__machine", "proxyinstance_set__machine"
    )
    if len(immute_domains) > 0:
        qs = qs.filter(bk_biz_id=bk_biz_id, immute_domain__in=immute_domains)
    else:
        qs = qs.filter(bk_biz_id=bk_biz_id)

    for cluster in qs:
        cluster_info = {
            "immute_domain": cluster.immute_domain,
            "storages": list(
                cluster.storageinstance_set.annotate(ip=F("machine__ip")).values("ip", "port", "instance_role")
            ),
            "proxies": list(
                cluster.proxyinstance_set.annotate(ip=F("machine__ip")).values("ip", "port", "admin_port")
            ),
            "cluster_type": cluster.cluster_type,
            "bk_biz_id": bk_biz_id,
            "db_module_id": cluster.db_module_id,
            "bk_cloud_id": cluster.bk_cloud_id,
        }

        res.append(cluster_info)

    return res
