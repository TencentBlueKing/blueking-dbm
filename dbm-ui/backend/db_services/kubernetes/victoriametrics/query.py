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

from backend.db_meta.enums import ClusterEntryRole
from backend.db_meta.models.cluster import Cluster
from backend.db_services.kubernetes.resources.query import KubernetesBaseListRetrieveResource
from backend.flow.utils.k8s_db.vm.consts import VMINSERT_PORT, VMSELECT_PORT


class VictoriaMetricsBaseListRetrieveResource(KubernetesBaseListRetrieveResource):
    fields = [
        *KubernetesBaseListRetrieveResource.fields,
    ]

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
        cluster_info.update(cls._get_victoriametrics_entries(cluster_info))
        return cluster_info

    @classmethod
    def _get_victoriametrics_entries(cls, cluster_info: Dict[str, Any]) -> Dict[str, str]:
        write_entry = cluster_info.get("master_domain", "")
        query_entry = cluster_info.get("slave_domain", "")
        for entry in cluster_info.get("cluster_entry", []):
            if entry.get("role") == ClusterEntryRole.MASTER_ENTRY.value:
                write_entry = entry.get("entry") or write_entry
            if entry.get("role") == ClusterEntryRole.SLAVE_ENTRY.value:
                query_entry = entry.get("entry") or query_entry
        return {
            "write_entry": cls._append_entry_port(write_entry, VMINSERT_PORT),
            "query_entry": cls._append_entry_port(query_entry, VMSELECT_PORT),
        }

    @classmethod
    def _append_entry_port(cls, entry: str, port: int) -> str:
        if not entry or entry.endswith(f":{port}"):
            return entry
        return f"{entry}:{port}"
