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
import itertools
import json
from typing import Dict

from django.db.models import Q, Count

from backend.db_meta.models import ProxyInstance, StorageInstance, Cluster, ClusterDeployPlan


class ToolboxHandler:
    def __init__(self, bk_biz_id: int):
        self.bk_biz_id = bk_biz_id

    def query_by_ip(self, ips) -> list:
        return list(itertools.chain(
            StorageInstance.filter_by_ips(self.bk_biz_id, ips),
            ProxyInstance.filter_by_ips(self.bk_biz_id, ips),
        ))

    def query_by_cluster(self, keywords, role="all") -> list:
        """根据角色和关键字查询集群规格、方案和角色信息"""
        number_keywords = filter(lambda x: x.isnumeric(), keywords)
        clusters = Cluster.objects.filter(
            Q(id__in=number_keywords) | Q(name__in=keywords) | Q(immute_domain__in=keywords),
            bk_biz_id=self.bk_biz_id
        )

        results = []
        for cluster in clusters:
            cluster_result: Dict[str, any] = {"cluster": cluster.extra_desc, "roles": []}
            if role in ["proxy", "all"]:
                cluster_result["roles"].append({
                    "name": "proxy",
                    "count": cluster.proxyinstance_set.all().count(),
                    "spec": cluster.proxyinstance_set.last().machine.spec_config,
                })

            if role in ["storage", "all"]:
                for storage in cluster.storageinstance_set.values("instance_role", "machine__spec_config").annotate(
                        role_count=Count('id')
                ).order_by():
                    cluster_result["roles"].append({
                        "role": storage["instance_role"],
                        "count": storage["role_count"],
                        "spec": json.loads(storage["machine__spec_config"])
                    })

            results.append(cluster_result)

        return results
