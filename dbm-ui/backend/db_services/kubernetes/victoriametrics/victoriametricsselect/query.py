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
from backend.db_meta.api.cluster.k8s_vm.victoriametricsselect.detail import scan_cluster
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models.cluster import Cluster
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.kubernetes.victoriametrics.query import VictoriaMetricsBaseListRetrieveResource
from backend.flow.utils.vm.consts import VMSTORAGE_NODE_START_PORT


@register_resource_decorator()
class VictoriaMetricsSelectListRetrieveResource(VictoriaMetricsBaseListRetrieveResource):
    cluster_types = [ClusterType.K8sVictoriametricsSelect]
    instance_roles = [InstanceRole.VM_SELECT]
    fields = [
        *VictoriaMetricsBaseListRetrieveResource.fields,
    ]

    @classmethod
    def _to_cluster_representation(cls, cluster: Cluster, *args, **kwargs) -> dict:
        cluster_info = super()._to_cluster_representation(cluster, *args, **kwargs)
        storage_nodes = []
        vmstorage_instances = cluster.storageinstance_set.filter(instance_role=InstanceRole.VM_STORAGE.value).order_by(
            "id"
        )
        for index, vmstorage in enumerate(vmstorage_instances):
            entry = vmstorage.bind_entry.first()
            if entry:
                domain = entry.entry
            else:
                related_cluster = vmstorage.cluster.exclude(id=cluster.id).first() or cluster
                domain = related_cluster.immute_domain
            storage_nodes.append(f"{domain}:{VMSTORAGE_NODE_START_PORT + index}")
        cluster_info["storage_nodes"] = storage_nodes
        return cluster_info

    @classmethod
    def get_topo_graph(
        cls, bk_biz_id: int, cluster_id: int, bcs_cluster_name: str = None, namespace: str = None
    ) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        return scan_cluster(cluster, bcs_cluster_name, namespace).to_dict()
