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

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.models import ProxyInstance
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import validate_clusters
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.ticket.builders.tendbcluster.tendb_cluster_spider_rebuild import TendbClusterSpiderRebuildDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

# 原地重建仅支持接入层的 master / slave 两种角色（不含 spider_ctl / spider_mnt / spider_slave_mnt）
SUPPORT_SPIDER_ROLES = [
    TenDBClusterSpiderRole.SPIDER_MASTER.value,
    TenDBClusterSpiderRole.SPIDER_SLAVE.value,
]


@bill_response_wrapper
def bill_spider_rebuild(username: str, cluster_domains: List[str], ips: List[str]):
    """
    创建 TenDBCluster 接入层（spider）原地重建单据。

    - 按 (cluster_id, spider_role) 分组，每个集群的每个接入层角色一行；
    - spider_ip_list 为该集群该角色下待重建的 spider 实例（ip:port）；
    - creator 使用实际操作者（username），helpers 默认空。
    """
    cluster_objs, bk_biz_id, bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBCluster)
    input_cluster_ids = set(cluster_objs.values_list("id", flat=True))

    if not ips:
        raise DBMMcpBaseException(msg=_("ips 不能为空"))

    spider_objs = list(
        ProxyInstance.objects.using(MYSQL_MCP_DB_READ)
        .filter(machine__ip__in=ips, machine__bk_cloud_id=bk_cloud_id)
        .select_related("machine", "tendbclusterspiderext")
        .prefetch_related("cluster")
    )

    found_ips = {si.machine.ip for si in spider_objs}
    missing_ips = set(ips) - found_ips
    if missing_ips:
        raise DBMMcpBaseException(msg=_("部分 IP 未找到对应 spider 实例: {}").format(sorted(missing_ips)))

    # 反查 spider 实例承载的集群并集，校验与输入集群一致（不多不少），防止跨集群 IP 被静默丢弃
    related_cluster_ids = set()
    for si in spider_objs:
        for cluster in si.cluster.all():
            related_cluster_ids.add(cluster.id)

    if related_cluster_ids != input_cluster_ids:
        extra = related_cluster_ids - input_cluster_ids
        missing = input_cluster_ids - related_cluster_ids
        raise DBMMcpBaseException(msg=_("输入集群与 spider 实例承载集群不一致, 缺少={}, 多余={}").format(sorted(missing), sorted(extra)))

    infos_map: Dict[Any, List[Dict[str, Any]]] = {}
    for si in spider_objs:
        spider_ext = getattr(si, "tendbclusterspiderext", None)
        spider_role = spider_ext.spider_role if spider_ext else None
        if spider_role not in SUPPORT_SPIDER_ROLES:
            raise DBMMcpBaseException(msg=_("IP {} 对应的 spider 角色 {} 不支持原地重建").format(si.machine.ip, spider_role))

        host_info = {
            "ip": si.machine.ip,
            "port": si.port,
            "bk_host_id": si.machine.bk_host_id,
            "bk_cloud_id": bk_cloud_id,
        }
        for cluster in si.cluster.all():
            if cluster.id in input_cluster_ids:
                infos_map.setdefault((cluster.id, spider_role), []).append(host_info)

    infos = [
        {
            "cluster_id": cluster_id,
            "spider_ip_list": hosts,
            "rebuild_spider_role": spider_role,
        }
        for (cluster_id, spider_role), hosts in sorted(infos_map.items())
    ]

    ticket_param = {
        "ticket_type": TicketType.TENDBCLUSTER_SPIDER_REBUILD,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "remark": TicketType.TENDBCLUSTER_SPIDER_REBUILD,
        "details": {"infos": infos},
    }

    slz = TendbClusterSpiderRebuildDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.TENDBCLUSTER_SPIDER_REBUILD
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    def _fingerprint(infos):
        return tuple(
            sorted(
                (
                    info["cluster_id"],
                    info["rebuild_spider_role"],
                    tuple(sorted(h["ip"] for h in info["spider_ip_list"])),
                )
                for info in infos
            )
        )

    existing = find_duplicate_ticket(
        ticket_type=TicketType.TENDBCLUSTER_SPIDER_REBUILD,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(infos),
        fingerprint_of=lambda tk: _fingerprint(tk.details.get("infos", [])),
    )
    if existing:
        return existing

    return Ticket.create_ticket(**ticket_param)
