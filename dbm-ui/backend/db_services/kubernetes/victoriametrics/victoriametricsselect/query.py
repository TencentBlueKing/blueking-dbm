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
from backend.components.kubernetes.client import KubernetesApi
from backend.db_meta.api.cluster.k8s_vm.victoriametricsselect.detail import scan_cluster
from backend.db_meta.enums import ClusterPhase, ClusterType, InstanceRole
from backend.db_meta.models.cluster import Cluster
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.kubernetes.victoriametrics.query import VictoriaMetricsBaseListRetrieveResource
from backend.flow.utils.k8s_db.vm.consts import COMPONENT_VMSELECT


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
        # 查询集群无 vminsert 组件，无写入口
        cluster_info["write_entry"] = ""
        # storage_nodes 需要请求第三方接口，列表只占位返回空列表，真实数据由详情接口返回
        cluster_info["storage_nodes"] = []
        return cluster_info

    @classmethod
    def _retrieve_cluster(cls, cluster_details: dict, cluster_id: int) -> dict:
        """集群详情补充外部 VMStorage 节点

        storage_nodes 需要请求第三方接口获取组件配置，只在详情接口返回；
        列表接口不再逐集群请求，避免 N+1 拖慢列表。
        """
        cluster_details = super()._retrieve_cluster(cluster_details, cluster_id)
        k8s_cluster_name = cluster_details.get("k8s_cluster_name", "")
        namespace = cluster_details.get("namespace", "")
        if k8s_cluster_name and namespace:
            cluster_details["storage_nodes"] = cls._get_storage_nodes(
                cluster_details.get("cluster_name", ""), cluster_details.get("phase", ""), k8s_cluster_name, namespace
            )
        else:
            cluster_details["storage_nodes"] = []
        return cluster_details

    @classmethod
    def _get_storage_nodes(cls, cluster_name: str, phase: str, bcs_cluster_name: str, namespace: str) -> list:
        """从 VMSelect 当前组件配置读取外部 VMStorage 节点，支持同步接入的集群。"""
        # 禁用集群不再查询组件配置
        if phase == ClusterPhase.OFFLINE.value:
            return []
        component = KubernetesApi.component_config(
            {
                "k8sClusterName": bcs_cluster_name,
                "clusterName": cluster_name,
                "namespace": namespace,
                "componentName": COMPONENT_VMSELECT,
            },
            use_admin=True,
        )
        storage_node = (component.get("config") or {}).get("storageNode") or ""
        return [node.strip() for node in storage_node.split(",") if node.strip()]

    @classmethod
    def get_topo_graph(
        cls, bk_biz_id: int, cluster_id: int, bcs_cluster_name: str = None, namespace: str = None
    ) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        storage_nodes = cls._get_storage_nodes(cluster.name, cluster.phase, bcs_cluster_name, namespace)
        return scan_cluster(cluster, bcs_cluster_name, namespace, storage_nodes).to_dict()
