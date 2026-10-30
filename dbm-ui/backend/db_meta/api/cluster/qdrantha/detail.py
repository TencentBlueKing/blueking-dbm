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
from backend.db_meta.enums import ClusterEntryType, InstanceRole
from backend.db_meta.models import Cluster


def scan_cluster(
    cluster: Cluster,
    k8s_cluster_name: str,
    namespace: str,
) -> Graphic:
    clb_dns = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLBDNS).first()
    graph = Graphic(node_id=clb_dns.entry if clb_dns else Graphic.generate_graphic_id(cluster))

    # 获取访问入口clb_dns和clb ip
    master_entry_group = Group(node_id="master_entry_group", group_name=_("访问入口"))
    # 域名在上、CLB IP 在下，和拓扑原型的入口卡片顺序一致
    entry_order = {
        ClusterEntryType.CLBDNS.value: 0,
        ClusterEntryType.CLB.value: 1,
    }
    clb_entries = sorted(
        cluster.clusterentry_set.filter(cluster_entry_type__in=[ClusterEntryType.CLBDNS, ClusterEntryType.CLB]),
        key=lambda entry: entry_order.get(entry.cluster_entry_type, 2),
    )
    for clb_entry in clb_entries:
        graph.add_node(clb_entry, to_group=master_entry_group)

    def get_instances(instance_role):
        data = {
            "k8sClusterName": k8s_cluster_name,
            "clusterName": cluster.name,
            "namespace": namespace,
            "componentName": instance_role,
        }
        resp = KubernetesApi.component_pods(data, use_admin=True)
        infos = [
            {
                "component_name": instance_role,
                "pod_name": res["podName"],
                "status": res["status"],
                "role": res.get("role") or "",
            }
            for res in resp.get("result", [])
        ]
        return infos

    # Pod 挂到分组 children_id，连线只从访问入口指向 Qdrant 分组。
    # Raft 角色写入 instance_state，供拓扑卡片展示 Leader / Follower。
    qdrant_infos = get_instances(InstanceRole.QDRANT)
    qdrant_group = Group(node_id=InstanceRole.QDRANT, group_name="Qdrant")
    for qdrant_info in qdrant_infos:
        node, __ = graph.add_node(qdrant_info, to_group=qdrant_group)
        node.instance_state = qdrant_info.get("role") or ""

    graph.add_line(source=master_entry_group, target=qdrant_group, label=LineLabel.Access)
    return graph
