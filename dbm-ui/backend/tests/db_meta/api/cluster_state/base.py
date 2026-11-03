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
from typing import Dict, List, Set

from django.utils.crypto import get_random_string

from backend.db_meta.api.cluster_state import ClusterStateService, StateValue
from backend.db_meta.api.cluster_state.filters import build_state_filter_q
from backend.db_meta.models import Cluster


def create_cluster(cluster_type: str, bk_biz_id: int, **kwargs) -> Cluster:
    name = get_random_string(8).lower()
    return Cluster.objects.create(
        name=name, cluster_type=cluster_type, immute_domain=f"{name}.state.db", bk_biz_id=bk_biz_id, **kwargs
    )


class StateFieldTestCase:
    """
    组件状态字段测试基类，组件为自己声明的字段写用例时继承使用：
        class TestTenDBHAStates(StateFieldTestCase):
            cluster_type = ClusterType.TenDBHA
    """

    cluster_type: str = ""

    @classmethod
    def cluster_info(cls, cluster: Cluster) -> Dict:
        """模拟列表接口的一行集群信息，用于 fill_states"""
        return {f.attname: getattr(cluster, f.attname) for f in Cluster._meta.concrete_fields}

    def get_states(self, clusters: List[Cluster]) -> Dict[int, Dict[str, StateValue]]:
        return ClusterStateService.batch_get([cluster.id for cluster in clusters])

    def get_state(self, cluster: Cluster, key: str) -> StateValue:
        return self.get_states([cluster])[cluster.id][key]

    def filter_cluster_ids(self, param: str, raw: str, clusters: List[Cluster]) -> Set[int]:
        """在给定集群范围内执行 state__ 过滤，返回命中的集群ID"""
        query = build_state_filter_q([self.cluster_type], {param: raw})
        queryset = Cluster.objects.filter(id__in=[cluster.id for cluster in clusters]).filter(query)
        return set(queryset.values_list("id", flat=True))
