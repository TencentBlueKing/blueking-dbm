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
import logging

from django.utils.translation import gettext as _

from backend.db_meta.api.cluster.base.graph import Graphic, Group, GroupNameType, LineLabel
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstanceTuple

logger = logging.getLogger("root")


def scan_cluster(cluster: Cluster) -> Graphic:
    """
    所有往 error report 中添加的信息都是集群的检查规则
    这部分应该抽象出去独立生成 report
    """
    graph = Graphic(node_id=Graphic.generate_graphic_id(cluster))

    for tr in (
        StorageInstanceTuple.objects.prefetch_related(
            "ejector__cluster",
            "receiver__cluster",
            "ejector__machine",
            "receiver__machine",
        )
        .filter(receiver__cluster=cluster, ejector__cluster=cluster)
        .order_by("-create_at")
    ):
        ejector_instance = tr.ejector
        receiver_instance = tr.receiver
        ejector_instance_node, ejector_instance_group = graph.add_node(ejector_instance)
        receiver_instance_node, receiver_instance_group = graph.add_node(receiver_instance)
        graph.add_line(source=ejector_instance_node, target=receiver_instance_node, label=LineLabel.Rep)

    # redis proxy 都直接指向所有后端，因此只需要连一条 group 的线即可
    proxy_instance = cluster.proxyinstance_set.first()
    proxy_instance_group = None
    for proxy_instance in cluster.proxyinstance_set.all():
        dummy_proxy_instance_node, proxy_instance_group = graph.add_node(proxy_instance, proxy_instance_group)
    master_backend_instance = proxy_instance.storageinstance.first()
    master_backend_instance_grp = graph.get_or_create_group(*Group.generate_group_info(master_backend_instance))
    graph.add_line(source=proxy_instance_group, target=master_backend_instance_grp, label=LineLabel.Access)

    # 主访问入口
    clb_entry_group = None
    master_entry_group = Group(node_id="master_entry_group", group_name=_("访问入口（{}）"))
    master_entry_names = []
    # redis的集群要获取master和proxy的entry作为访问入口
    master_proxy_entry = cluster.clusterentry_set.filter(
        role__in=[ClusterEntryRole.MASTER_ENTRY.value, ClusterEntryRole.PROXY_ENTRY.value]
    ).all()
    if master_proxy_entry.filter(cluster__clusterentry__cluster_entry_type=ClusterEntryType.CLB).exists():
        clb_entry_group = Group(node_id="clb_entry_group", group_name=_("访问入口（CLB IP）"))
    for entry in master_proxy_entry:
        # clb肯定指向proxy
        if entry.cluster_entry_type == ClusterEntryType.CLB:
            dummy_be_node, clb_entry_group = graph.add_node(entry, to_group=clb_entry_group)
            graph.add_line(source=clb_entry_group, target=proxy_instance_group, label=LineLabel.Forward)

        # clbDNS肯定指向clb
        elif entry.cluster_entry_type == ClusterEntryType.CLBDNS:
            clb_dns_entry_group = Group(node_id="clb_dns_entry_group", group_name=_("访问入口（CLB域名）"))
            dummy_be_node, clb_dns_entry_group = graph.add_node(entry, to_group=clb_dns_entry_group)
            graph.add_line(source=clb_dns_entry_group, target=clb_entry_group, label=LineLabel.Bind)

        # dns默认指向proxy 指向clb之后不再指向proxy
        elif entry.cluster_entry_type == ClusterEntryType.DNS:
            if entry.forward_to:
                dns_entry_group = Group(node_id="dns_entry_group", group_name=_("访问入口（主域名）"))
                dummy_be_node, dns_entry_group = graph.add_node(entry, to_group=dns_entry_group)
                graph.add_line(source=dns_entry_group, target=clb_entry_group, label=LineLabel.Bind)

            else:
                dummy_be_node, master_entry_group = graph.add_node(entry, to_group=master_entry_group)
                graph.add_line(source=master_entry_group, target=proxy_instance_group, label=LineLabel.Bind)
                master_entry_names.append(str(GroupNameType.get_choice_label(GroupNameType.DNS.value)))

        # 北极星目前只指向proxy
        else:
            dummy_be_node, master_entry_group = graph.add_node(entry, to_group=master_entry_group)
            graph.add_line(source=master_entry_group, target=proxy_instance_group, label=LineLabel.Bind)
            master_entry_names.append(str(GroupNameType.get_choice_label(GroupNameType.POLARIS.value)))

    master_entry_group.group_name = master_entry_group.group_name.format("、".join(master_entry_names))

    # 存储层访问入口
    nodes_bind_entry_group = Group(node_id="nodes_bind_entry_group", group_name=_("存储层访问入口"))
    for bind_entry in master_backend_instance.bind_entry.filter(role=ClusterEntryRole.NODE_ENTRY.value):
        dummy_be_node, nodes_bind_entry_group = graph.add_node(bind_entry, to_group=nodes_bind_entry_group)
        graph.add_line(source=nodes_bind_entry_group, target=master_backend_instance_grp, label=LineLabel.Bind)

    # slave 存储访问入口
    slave_instance = cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.SLAVE.value).first()
    slave_instance_group = graph.get_or_create_group(*Group.generate_group_info(slave_instance))
    for bind_entry in master_backend_instance.bind_entry.filter(role=ClusterEntryRole.NODE_ENTRY.value):
        dummy_be_node, nodes_bind_entry_group = graph.add_node(bind_entry, to_group=nodes_bind_entry_group)
        graph.add_line(source=nodes_bind_entry_group, target=slave_instance_group, label=LineLabel.Bind)

    return graph
