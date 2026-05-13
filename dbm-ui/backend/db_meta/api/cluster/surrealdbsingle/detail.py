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
from backend.db_meta.enums import ClusterEntryType, KubernetesInstanceRole
from backend.db_meta.models import Cluster


def scan_cluster(
    cluster: Cluster,
    k8s_cluster_name: str,
    namespace: str,
) -> Graphic:
    clb_dns = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLBDNS).first()
    graph = Graphic(node_id=clb_dns.entry)

    # 获取访问入口clb_dns和clb ip
    master_entry_group = Group(node_id="master_entry_group", group_name=_("访问入口"))
    clb_entries = cluster.clusterentry_set.filter(
        cluster_entry_type__in=[ClusterEntryType.CLBDNS, ClusterEntryType.CLB]
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
            {"component_name": instance_role, "pod_name": res["podName"], "status": res["status"]}
            for res in resp.get("result", [])
        ]
        return infos

    # 获取集群surreal实例
    surreal_infos = get_instances(KubernetesInstanceRole.SURREAL)
    surreal_group = Group(node_id=KubernetesInstanceRole.SURREAL, group_name="Surreal")
    for surreal_info in surreal_infos:
        graph.add_node(surreal_info, to_group=surreal_group)

    graph.add_line(source=master_entry_group, target=surreal_group, label=LineLabel.Access)
    return graph
