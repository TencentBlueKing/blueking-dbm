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
from backend.db_meta.api.cluster.surrealdb.surrealdbha.detail import scan_cluster
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models.cluster import Cluster
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.kubernetes.resources.query import KubernetesBaseListRetrieveResource


@register_resource_decorator()
class SurrealDBHaListRetrieveResource(KubernetesBaseListRetrieveResource):
    cluster_types = [ClusterType.K8sSurrealdbHa]
    instance_roles = [InstanceRole.SURREAL, InstanceRole.TIKV, InstanceRole.PD]
    fields = [
        *KubernetesBaseListRetrieveResource.fields,
    ]

    @classmethod
    def get_topo_graph(
        cls, bk_biz_id: int, cluster_id: int, bcs_cluster_name: str = None, namespace: str = None
    ) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        graph = scan_cluster(cluster, bcs_cluster_name, namespace).to_dict()
        return graph
