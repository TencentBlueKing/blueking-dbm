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
from rest_framework import serializers

from .query import QdrantHaListRetrieveResource

REF_NAME = "qdrantha"

paginated_resource_example = {
    "count": 10,
    "next": "http://xxxxx?limit=5&offset=10",
    "previous": "http://xxxxx?limit=5&offset=10",
    "results": [
        {
            "cluster_name": "bk-dbm",
            "master_domain": "qdrant.bk-dbm.blueking.db",
            # Qdrant 使用 Raft 对等节点，没有 master/slave 概念
            "peers": [
                {"node_ip": "0.0.0.1", "node_port": 6333, "node_role": "peer", "status": "healthy"},
                {"node_ip": "0.0.0.2", "node_port": 6333, "node_role": "peer", "status": "healthy"},
                {"node_ip": "0.0.0.3", "node_port": 6333, "node_role": "peer", "status": "healthy"},
            ],
            "bcs_cluster_name": "k8s-cluster-001",
            "namespace": "qdrant-namespace",
            "version": "v1.8.0",
            "status": "running",
            "create_at": "2024-01-01 10:00:00",
            "update_at": "2024-01-01 10:00:00",
            "creator": "admin",
            "updater": "admin",
            "...": "...",
        }
    ],
}

resource_topo_graph_example = {
    "node_id": "qdrant-cluster-db.ha-test2.blueking.db:6333",
    "nodes": [
        {"node_id": "qdrant-pod-0", "node_type": "qdrant::peer_node"},
        {"node_id": "qdrant-pod-1", "node_type": "qdrant::peer_node"},
        {"node_id": "qdrant-pod-2", "node_type": "qdrant::peer_node"},
        {"node_id": "qdrant-cluster-db.ha-test2.blueking.db:6333", "node_type": "entry_dns"},
    ],
    "groups": [
        {
            "node_id": "qdrant::peer_nodes",
            "children_id": ["qdrant-pod-0", "qdrant-pod-1", "qdrant-pod-2"],
        },
        {"node_id": "entry_dns", "children_id": ["qdrant-cluster-db.ha-test2.blueking.db"]},
    ],
    "lines": [
        {
            "source": "qdrant-pod-0",
            "source_type": "node",
            "target": "qdrant-pod-1",
            "target_type": "node",
            "label": "raft",
        },
        {
            "source": "qdrant-pod-0",
            "source_type": "node",
            "target": "qdrant-pod-2",
            "target_type": "node",
            "label": "raft",
        },
        {
            "source": "qdrant-pod-1",
            "source_type": "node",
            "target": "qdrant-pod-2",
            "target_type": "node",
            "label": "raft",
        },
        {
            "source": "qdrant-cluster-db.ha-test2.blueking.db",
            "source_type": "node",
            "target": "qdrant::peer_nodes",
            "target_type": "group",
            "label": "access",
        },
    ],
    "foreign_relations": {"raft_to": [], "raft_from": [], "access_to": [], "access_from": []},
}


class PaginatedResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_resource_example}
        ref_name = f"{REF_NAME}_PaginatedResourceSLZ"


class ResourceFieldSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": QdrantHaListRetrieveResource.get_fields()}
        ref_name = f"{REF_NAME}_ResourceFieldSLZ"


class ResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": paginated_resource_example["results"][0]}
        ref_name = f"{REF_NAME}_ResourceSLZ"


class ResourceTopoGraphSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": resource_topo_graph_example}
        ref_name = f"{REF_NAME}_ResourceTopoGraphSLZ"


class PasswordResourceSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {
            "example": {"cluster_name": "qdrant1", "domain": "qdrant.tendis.dd.abc.db", "password": "123456"}
        }
        ref_name = f"{REF_NAME}_PasswordResourceSLZ"
