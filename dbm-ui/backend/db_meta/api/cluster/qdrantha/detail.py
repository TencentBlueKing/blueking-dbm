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

from django.utils.translation import gettext as _

from backend.components.kubernetes.client import KubernetesApi
from backend.db_meta.api.cluster.base.graph import Graphic, Group, LineLabel
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster


def scan_cluster(
    cluster: Cluster,
    k8s_cluster_name: str,
    namespace: str,
) -> Graphic:
    clb_dns = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLBDNS).first()
    graph = Graphic(node_id=clb_dns.entry if clb_dns else Graphic.generate_graphic_id(cluster))

    # 获取访问入口clb_dns和clb ip
    entry_group = Group(node_id="entry_group", group_name=_("访问入口"))
    clb_entries = cluster.clusterentry_set.filter(
        cluster_entry_type__in=[ClusterEntryType.CLBDNS, ClusterEntryType.CLB]
    )
    for clb_entry in clb_entries:
        graph.add_node(clb_entry, to_group=entry_group)

    data = {
        "k8sClusterName": k8s_cluster_name,
        "clusterName": cluster.name,
        "namespace": namespace,
        "componentName": "qdrant",
    }
    resp = KubernetesApi.component_pods(data, use_admin=True)

    peer_group = Group(node_id="qdrant", group_name="Qdrant")
    for pod in resp.get("result", []):
        graph.add_node(
            {
                "component_name": "qdrant",
                "pod_name": pod.get("podName"),
                "status": pod.get("status"),
            },
            to_group=peer_group,
        )

    if clb_entries.exists() and peer_group.children_id:
        graph.add_line(source=entry_group, target=peer_group, label=LineLabel.Access)

    return graph
