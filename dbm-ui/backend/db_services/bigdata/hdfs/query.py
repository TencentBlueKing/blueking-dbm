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

from typing import Any, Dict, List, Set

from django.utils.translation import ugettext_lazy as _

from backend.db_meta.api.cluster.hdfs.detail import scan_cluster
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.bigdata.resources.query import BigDataBaseListRetrieveResource
from backend.db_services.dbbase.resources import query


class HDFSListRetrieveResource(BigDataBaseListRetrieveResource):
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
    def _to_nodes_list(
        cls, bk_biz_id: int, node_list: List[Dict[str, Any]], limit: int, offset: int
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

        return super()._to_nodes_list(bk_biz_id, list(ip__hdfs_node_list.values()), limit, offset)

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        graph = scan_cluster(cluster).to_dict()
        return graph
