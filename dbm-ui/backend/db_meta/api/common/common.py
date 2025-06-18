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
from typing import Dict, List

from django.db.models import Q, QuerySet
from django.utils.translation import gettext as _

from backend.db_meta.api.cluster.base.graph import Group, GroupNameType, LineLabel
from backend.db_meta.enums import ClusterEntryType

logger = logging.getLogger("root")


def in_another_cluster(instances: QuerySet) -> List[Dict]:
    return list(instances.filter(cluster__isnull=False))


def filter_out_instance_obj(instances: List[Dict], qs: QuerySet) -> QuerySet:
    queries = Q()
    for i in instances:
        queries |= Q(**{"machine__ip": i["ip"], "port": i["port"]})

    return qs.filter(queries)


def not_exists(instances: List[Dict], qs: QuerySet) -> List[Dict]:
    ne = set(map(lambda e: (e["ip"], e["port"]), instances)) - set(qs.values_list("machine__ip", "port"))
    return list(map(lambda e: {"ip": e[0], "port": e[1]}, ne))


def equ_list_of_dict(a, b: List) -> bool:
    d1 = [e for e in a if e not in b]
    d2 = [e for e in b if e not in a]
    logger.debug("{} {} {} {}".format(a, b, d1, d2))
    if d1 or d2:
        return False
    return True


def remain_instance_obj(instances: List[Dict], qs: QuerySet) -> List[Dict]:
    ne = set(qs.values_list("machine__ip", "port")) - set(map(lambda e: (e["ip"], e["port"]), instances))
    return list(map(lambda e: {"ip": e[0], "port": e[1]}, ne))


def get_clb_topo(graph, all_entry, proxy_group):
    clb_entry_group = None
    entry_group = Group(node_id="master_entry_group", group_name=_("{}"))
    master_entry_names = []
    if all_entry.filter(cluster__clusterentry__cluster_entry_type=ClusterEntryType.CLB).exists():
        clb_entry_group = Group(node_id="clb_entry_group", group_name=_("CLB IP"))

    for entry in all_entry:
        # clb肯定指向proxy
        if entry.cluster_entry_type == ClusterEntryType.CLB:
            dummy_be_node, clb_entry_group = graph.add_node(entry, to_group=clb_entry_group)
            graph.add_line(source=clb_entry_group, target=proxy_group, label=LineLabel.Forward)

            # clbDNS肯定指向clb
        elif entry.cluster_entry_type == ClusterEntryType.CLBDNS:
            clb_dns_entry_group = Group(node_id="clb_dns_entry_group", group_name=_("CLB域名"))
            dummy_be_node, clb_dns_entry_group = graph.add_node(entry, to_group=clb_dns_entry_group)
            graph.add_line(source=clb_dns_entry_group, target=clb_entry_group, label=LineLabel.Bind)

        # dns默认指向proxy 指向clb之后不再指向proxy
        elif entry.cluster_entry_type == ClusterEntryType.DNS:
            if entry.forward_to:
                dns_entry_group = Group(node_id="dns_entry_group", group_name=_("主域名"))
                dummy_be_node, dns_entry_group = graph.add_node(entry, to_group=dns_entry_group)
                graph.add_line(source=dns_entry_group, target=clb_entry_group, label=LineLabel.Bind)

            else:
                dummy_be_node, entry_group = graph.add_node(entry, to_group=entry_group)
                graph.add_line(source=entry_group, target=proxy_group, label=LineLabel.Bind)
                master_entry_names.append(str(GroupNameType.get_choice_label(GroupNameType.DNS.value)))

        # 北极星目前只指向proxy
        else:
            dummy_be_node, entry_group = graph.add_node(entry, to_group=entry_group)
            graph.add_line(source=entry_group, target=proxy_group, label=LineLabel.Bind)
            master_entry_names.append(str(GroupNameType.get_choice_label(GroupNameType.POLARIS.value)))

    entry_group.group_name = entry_group.group_name.format("、".join(master_entry_names))

    return graph
