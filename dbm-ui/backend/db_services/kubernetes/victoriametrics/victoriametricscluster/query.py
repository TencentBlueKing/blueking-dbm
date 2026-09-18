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
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _

from backend.components.kubernetes.client import KubernetesApi
from backend.db_meta.api.cluster.k8s_vm.victoriametricscluster.detail import scan_cluster
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models.cluster import Cluster
from backend.db_services.dbbase.resources.query import ResourceList
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.kubernetes.victoriametrics.query import VictoriaMetricsBaseListRetrieveResource
from backend.exceptions import AppBaseException
from backend.flow.utils.k8s_db.vm.consts import (
    COMPONENT_VMINSERT,
    COMPONENT_VMSELECT,
    COMPONENT_VMSTORAGE,
    VMINSERT_SERVICE_NAME,
    VMSELECT_SERVICE_NAME,
)
from backend.flow.utils.vm.consts import VMSTORAGE_NODE_START_PORT

# CLB ID 标注键，按优先级排序
CLB_ID_ANNOTATION_KEYS = [
    "service.kubernetes.io/tke-existed-lbid",
    "service.kubernetes.io/loadbalance-id",
]

# 源 Service：组件名 -> 暴露的 Service 名（完整名为 {cluster_name}-{component_name}-{service_name}）
SOURCE_SERVICE_NAMES = {
    COMPONENT_VMINSERT: VMINSERT_SERVICE_NAME,
    COMPONENT_VMSELECT: VMSELECT_SERVICE_NAME,
}


@register_resource_decorator()
class VictoriaMetricsClusterListRetrieveResource(VictoriaMetricsBaseListRetrieveResource):
    cluster_types = [ClusterType.K8sVictoriametricsCluster]
    instance_roles = [InstanceRole.VM_INSERT, InstanceRole.VM_SELECT, InstanceRole.VM_STORAGE]
    fields = [
        *VictoriaMetricsBaseListRetrieveResource.fields,
    ]

    @classmethod
    def get_topo_graph(
        cls, bk_biz_id: int, cluster_id: int, bcs_cluster_name: str = None, namespace: str = None
    ) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        return scan_cluster(cluster, bcs_cluster_name, namespace).to_dict()

    @classmethod
    def _to_cluster_representation(
        cls,
        cluster: Cluster,
        cluster_entry: List[Dict[str, str]],
        db_module_names_map: Dict[int, str],
        cluster_entry_map: Dict[int, Dict[str, str]],
        cluster_operate_records_map: Dict[int, List],
        cloud_info: Dict[str, Any],
        biz_info,
        cluster_stats_map: Dict[str, Dict[str, int]],
        cluster_zone_map: Dict[str, str],
        dns_to_clb: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        cluster_info = super()._to_cluster_representation(
            cluster,
            cluster_entry,
            db_module_names_map,
            cluster_entry_map,
            cluster_operate_records_map,
            cloud_info,
            biz_info,
            cluster_stats_map,
            cluster_zone_map,
            dns_to_clb,
            **kwargs,
        )
        cluster_info["storage_entry"] = cls._get_storage_entry(cluster)
        return cluster_info

    @classmethod
    def _get_storage_entry(cls, cluster: Cluster, context: dict = None) -> str:
        """vmstorage 存储入口：统一域名 + 按实例序号从 8000 递增的端口"""
        context = context or cls.get_cluster_context(cluster)
        pods = (
            KubernetesApi.component_pods(
                {
                    "k8sClusterName": context["k8s_cluster_name"],
                    "clusterName": context["cluster_name"],
                    "namespace": context["namespace"],
                    "componentName": COMPONENT_VMSTORAGE,
                },
                use_admin=True,
            )
            or {}
        )
        storage_count = len(pods.get("result") or [])
        return "\n".join(
            f"{cluster.immute_domain}:{VMSTORAGE_NODE_START_PORT + index}" for index in range(storage_count)
        )

    @classmethod
    def _list_instances(
        cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int, filter_params_map: Dict = None, **kwargs
    ) -> ResourceList:
        resource_list = super()._list_instances(bk_biz_id, query_params, limit, offset, filter_params_map, **kwargs)
        cluster_clb_enabled_map = cls._get_cluster_clb_enabled_map(query_params)
        cluster_name_id_map = cls._get_cluster_name_id_map(bk_biz_id, query_params)
        cluster_id_enabled_map = {
            cluster_id: cluster_clb_enabled_map.get(cluster_name, False)
            for cluster_name, cluster_id in cluster_name_id_map.items()
        }

        for instance in resource_list.data:
            instance["is_clb_enabled"] = cluster_id_enabled_map.get(instance.get("cluster_id"), False)

        return resource_list

    @classmethod
    def _get_cluster_clb_enabled_map(cls, query_params: Dict) -> Dict[str, bool]:
        cluster_names = query_params.get("cluster_name", "")
        k8s_cluster_names = query_params.get("k8s_cluster_name", "")
        namespaces = query_params.get("namespace", "")

        cluster_name_list = cluster_names.split(",") if cluster_names else []
        k8s_cluster_name_list = k8s_cluster_names.split(",") if k8s_cluster_names else []
        namespace_list = namespaces.split(",") if namespaces else []

        if len(cluster_name_list) != len(k8s_cluster_name_list) or len(cluster_name_list) != len(namespace_list):
            raise ValueError(_("cluster_name, k8s_cluster_name, namespace 参数数量必须一致"))

        cluster_clb_enabled_map = {}
        for cluster_name, k8s_cluster_name, namespace in zip(cluster_name_list, k8s_cluster_name_list, namespace_list):
            params = {
                "k8sClusterName": k8s_cluster_name,
                "clusterName": cluster_name,
                "namespace": namespace,
            }
            res = KubernetesApi.cluster_services(params, use_admin=True) or {}
            component_services = res.get("componentServices") or []
            cluster_clb_enabled_map[cluster_name] = any(
                component_service.get("externalServiceInfo") for component_service in component_services
            )

        return cluster_clb_enabled_map

    @classmethod
    def _get_cluster_name_id_map(cls, bk_biz_id: int, query_params: Dict) -> Dict[str, int]:
        cluster_names = query_params.get("cluster_name", "")
        cluster_name_list = cluster_names.split(",") if cluster_names else []
        if not cluster_name_list:
            return {}

        clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id, name__in=cluster_name_list).only("id", "name")
        return {cluster.name: cluster.id for cluster in clusters}

    @classmethod
    def set_vmstorage_clb_enabled(cls, bk_biz_id: int, cluster_id: int, enable: bool, bk_username: str) -> dict:
        """启用/停用 vmstorage 实例级 CLB 暴露，返回 DBS 处理结果"""
        cluster = cls.get_cluster(bk_biz_id, cluster_id)
        context = cls.get_cluster_context(cluster)
        load_balancer_id = cls.get_source_load_balancer(context)
        result = (
            KubernetesApi.expose_instance(
                {
                    "dbmClusterId": cluster_id,
                    "k8sClusterName": context["k8s_cluster_name"],
                    "clusterName": context["cluster_name"],
                    "namespace": context["namespace"],
                    "enable": enable,
                    "loadBalancerId": load_balancer_id,
                    "bk_username": bk_username,
                }
            )
            or {}
        )
        result["storage_entry"] = cls._get_storage_entry(cluster, context) if enable else ""
        return result

    @classmethod
    def get_cluster(cls, bk_biz_id: int, cluster_id: int) -> Cluster:
        """校验集群存在且属于当前业务，且为 VM 标准集群（查询版集群无 vmstorage 组件）"""
        try:
            cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        except Cluster.DoesNotExist:
            raise AppBaseException(_("集群不存在"))
        if cluster.cluster_type != ClusterType.K8sVictoriametricsCluster.value:
            raise AppBaseException(_("该操作仅支持 K8s VictoriaMetrics 标准集群"))
        return cluster

    @classmethod
    def get_cluster_context(cls, cluster: Cluster) -> dict:
        """通过 DBS 元数据获取集群身份并交叉校验

        :return: {"k8s_cluster_name", "cluster_name", "namespace"}
        """
        detail = KubernetesApi.cluster_detail({"cluster_id": cluster.id}, use_admin=True) or {}
        if detail.get("clusterName") != cluster.name:
            raise AppBaseException(_("集群元数据校验失败，请确认集群是否正常"))

        context = {
            "k8s_cluster_name": (detail.get("k8sClusterConfig") or {}).get("clusterName"),
            "cluster_name": detail.get("clusterName"),
            "namespace": detail.get("namespace"),
        }
        if not all(context.values()):
            raise AppBaseException(_("集群元数据信息不完整，请联系管理员"))
        return context

    @classmethod
    def get_source_load_balancer(cls, context: dict) -> str:
        """从 vminsert-clb / vmselect-clb 两个源 Service 提取共享 CLB ID 并互验一致"""
        response = (
            KubernetesApi.cluster_services(
                {
                    "k8sClusterName": context["k8s_cluster_name"],
                    "clusterName": context["cluster_name"],
                    "namespace": context["namespace"],
                },
                use_admin=True,
            )
            or {}
        )
        component_services = response.get("componentServices") or []

        load_balancer_ids = [
            cls.extract_component_load_balancer(
                component_services, component_name, f"{context['cluster_name']}-{component_name}-{service_name}"
            )
            for component_name, service_name in SOURCE_SERVICE_NAMES.items()
        ]

        if not all(load_balancer_ids):
            raise AppBaseException(_("vminsert/vmselect CLB 尚未就绪，请稍后重试"))
        if len(set(load_balancer_ids)) != 1:
            raise AppBaseException(_("源 CLB 信息异常，请联系管理员"))
        return load_balancer_ids[0]

    @classmethod
    def extract_component_load_balancer(
        cls, component_services: list, component_name: str, expected_service_name: str
    ) -> str:
        """定位指定组件的源 Service，并从 annotations 提取 CLB ID；找不到时返回空字符串"""
        for component in component_services:
            if component.get("componentName") != component_name:
                continue
            for external_service in component.get("externalServiceInfo") or []:
                if external_service.get("serviceName") != expected_service_name:
                    continue
                return cls.extract_load_balancer_id(external_service.get("annotations") or {})
        return ""

    @classmethod
    def extract_load_balancer_id(cls, annotations: dict) -> str:
        """按优先级从 annotations 提取 CLB ID；两个 key 同时存在且不一致时视为冲突，不猜测"""
        values = {key: annotations[key] for key in CLB_ID_ANNOTATION_KEYS if annotations.get(key)}
        if len(set(values.values())) > 1:
            raise AppBaseException(_("源 CLB 信息异常，请联系管理员"))
        for key in CLB_ID_ANNOTATION_KEYS:
            if annotations.get(key):
                return annotations[key]
        return ""
