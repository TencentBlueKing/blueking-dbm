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

import json
from typing import Any, Dict, List, Set

from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from backend.db_meta.api.cluster.hdfs.detail import scan_cluster
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.bigdata.resources.query import (
    BigDataBaseExportQueryResourceMixin,
    BigDataBaseListRetrieveResource,
)
from backend.db_services.dbbase.resources import query
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.flow.utils.hdfs.consts import CACHE_CLUSTER_MASTER


class HDFSExportQueryResourceMixin(BigDataBaseExportQueryResourceMixin):
    """补充HDFS集群列表导出所需的header及数据"""

    @classmethod
    def update_headers(cls, headers, **kwargs):
        # 补充实例为空未展示的字段
        extra_headers = [
            {"id": "hdfs_namenode", "name": _("NameNode")},
            {"id": "hdfs_zookeeper", "name": _("Zookeeper")},
            {"id": "hdfs_journalnode", "name": _("Journalnode")},
            {"id": "hdfs_datanode", "name": _("DataNode")},
        ]

        return super().update_headers(headers, extra_headers=extra_headers)


@register_resource_decorator()
class HDFSListRetrieveResource(BigDataBaseListRetrieveResource, HDFSExportQueryResourceMixin):
    cluster_types = [ClusterType.Hdfs]
    instance_roles = [
        InstanceRole.HDFS_ZOOKEEPER.value,
        InstanceRole.HDFS_DATA_NODE.value,
        InstanceRole.HDFS_NAME_NODE.value,
        InstanceRole.HDFS_JOURNAL_NODE.value,
    ]
    fields = [
        *BigDataBaseListRetrieveResource.fields,
        {"name": _("namenode节点"), "key": "hdfs_namenode"},
        {"name": _("zookeeper节点"), "key": "hdfs_zookeeper"},
        {"name": _("journalnode节点"), "key": "hdfs_journalnode"},
        {"name": _("datanode节点"), "key": "hdfs_datanode"},
    ]

    @classmethod
    def _filter_cluster_hook(
        cls, bk_biz_id, cluster_queryset, proxy_queryset, storage_queryset, limit: int, offset: int, **kwargs
    ):
        count = cluster_queryset.count()
        limit = count if limit == -1 else limit
        cluster_ids = list(cluster_queryset.values_list("id", flat=True)[offset : limit + offset])
        kwargs["active_namenode_map"] = cls.get_clusters_master(bk_biz_id, cluster_ids)
        return super()._filter_cluster_hook(
            bk_biz_id, cluster_queryset, proxy_queryset, storage_queryset, limit, offset, **kwargs
        )

    @classmethod
    def _to_cluster_representation(cls, cluster: Cluster, *args, **kwargs) -> Dict[str, Any]:
        cluster_info = super()._to_cluster_representation(cluster, *args, **kwargs)
        active_namenode = kwargs.get("active_namenode_map", {}).get(cluster.id, "")

        for namenode in cluster_info.get(InstanceRole.HDFS_NAME_NODE.value, []):
            namenode["is_active"] = namenode["instance"] == active_namenode

        return cluster_info

    @classmethod
    def _filter_instance_hook(cls, bk_biz_id, query_params, instances, **kwargs):
        instances = list(instances)
        cluster_ids = list({instance["cluster__id"] for instance in instances})
        kwargs["active_namenode_map"] = cls.get_clusters_master(bk_biz_id, cluster_ids)
        return super()._filter_instance_hook(bk_biz_id, query_params, instances, **kwargs)

    @classmethod
    def _to_instance_representation(
        cls, instance: dict, cluster_entry_map: dict, db_module_names_map: dict, **kwargs
    ) -> Dict[str, Any]:
        instance_info = super()._to_instance_representation(instance, cluster_entry_map, db_module_names_map, **kwargs)
        active_namenode = kwargs.get("active_namenode_map", {}).get(instance["cluster__id"], "")
        instance_info["is_active"] = (
            instance["role"] == InstanceRole.HDFS_NAME_NODE.value
            and instance_info["instance_address"] == active_namenode
        )
        return instance_info

    @classmethod
    def _to_nodes_list(
        cls, bk_biz_id: int, node_list: List[Dict[str, Any]], limit: int, offset: int, ordering: str
    ) -> query.ResourceList:

        # 将zookeeper/name node/journal node 聚合到一起
        ip__hdfs_node_list: Dict[List[Dict[str, Any]]] = {}
        for node in node_list:
            ip = node["machine__ip"]
            if not ip__hdfs_node_list.get(ip):
                ip__hdfs_node_list[ip] = node
                ip__hdfs_node_list[ip]["role_set"]: Set[str] = {
                    node.pop("role"),
                }
            else:
                ip__hdfs_node_list[ip]["role_set"].add(node["role"])
                ip__hdfs_node_list[ip]["node_count"] += node["node_count"]

        # 对角色进行排序，利于前端展示
        for node_list in ip__hdfs_node_list.values():
            node_list["role_set"] = sorted(list(node_list["role_set"]))

        return super()._to_nodes_list(bk_biz_id, list(ip__hdfs_node_list.values()), limit, offset, ordering)

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        graph = scan_cluster(cluster).to_dict()
        return graph

    @classmethod
    def get_clusters_master(cls, bk_biz_id: int, cluster_ids: list) -> dict:
        """
        获取 HDFS 集群 Active NameNode 信息，只从 Cache 中获取

        Cache 由 db_periodic_task.local_tasks.hdfs.sync_cluster_master 定时任务写入，
        key 格式: {CACHE_CLUSTER_MASTER}_{bk_biz_id}_{cluster_type}
        value 格式: JSON {cluster_domain: active_host}

        Returns:
            dict: {cluster_id: active_host}
        """
        cluster_ids = cluster_ids or []
        cache_master_stats: Dict[str, str] = {}
        for cluster_type in cls.cluster_types:
            raw = cache.get(f"{CACHE_CLUSTER_MASTER}_{bk_biz_id}_{cluster_type.value}", "{}")
            cache_master_stats.update(json.loads(raw))

        # 集群 immute_domain -> id 映射
        cluster_domain_qs = Cluster.objects.filter(
            bk_biz_id=bk_biz_id, id__in=cluster_ids, cluster_type=ClusterType.Hdfs
        ).values("immute_domain", "id")
        domain_ids = {cluster["immute_domain"]: cluster["id"] for cluster in cluster_domain_qs}

        return {domain_ids[domain]: master for domain, master in cache_master_stats.items() if domain in domain_ids}
