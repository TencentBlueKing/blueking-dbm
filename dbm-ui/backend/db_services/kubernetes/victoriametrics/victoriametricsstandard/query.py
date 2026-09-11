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
from backend.db_meta.api.cluster.k8s_vm.victoriametricsstandard.detail import scan_cluster
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models.cluster import Cluster
from backend.db_services.dbbase.resources.query import ResourceList
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.kubernetes.victoriametrics.query import VictoriaMetricsBaseListRetrieveResource


@register_resource_decorator()
class VictoriaMetricsStandardListRetrieveResource(VictoriaMetricsBaseListRetrieveResource):
    cluster_types = [ClusterType.K8sVictoriametricsCluster]
    instance_roles = [InstanceRole.VM_INSERT, InstanceRole.VM_SELECT, InstanceRole.VM_STORAGE]
    fields = [
        {"name": _("存储入口"), "key": "storage_entry"},
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
    def _get_storage_entry(cls, cluster: Cluster) -> str:
        storage_instances = getattr(cluster, "storages", cluster.storageinstance_set.all())
        return "\n".join(
            inst.ip_port for inst in storage_instances if inst.instance_role == InstanceRole.VM_STORAGE.value
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
