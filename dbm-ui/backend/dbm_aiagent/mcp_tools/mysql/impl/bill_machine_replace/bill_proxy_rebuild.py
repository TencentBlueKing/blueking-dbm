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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import ProxyInstance
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import validate_clusters
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.ticket.builders.mysql.mysql_proxy_rebuild import MysqlProxyRebuildDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_proxy_rebuild(username: str, cluster_domains: List[str], ips: List[str]):
    """
    创建 TenDBHA proxy 原地重建单据。

    - 每行一个集群，重建该集群下的 proxy 实例（ip:port）；
    - 自动按 proxy 实例的 cluster 关联关系补齐同机关联集群；
    - creator 使用实际操作者（username），helpers 默认空。
    """
    cluster_objs, bk_biz_id, bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBHA)
    input_cluster_ids = set(cluster_objs.values_list("id", flat=True))

    if not ips:
        raise DBMMcpBaseException(msg=_("ips 不能为空"))

    proxy_objs = list(
        ProxyInstance.objects.using(MYSQL_MCP_DB_READ)
        .filter(machine__ip__in=ips, machine__bk_cloud_id=bk_cloud_id)
        .select_related("machine")
        .prefetch_related("cluster")
    )

    # 校验每个 IP 都能找到对应 proxy 实例
    found_ips = {pi.machine.ip for pi in proxy_objs}
    missing_ips = set(ips) - found_ips
    if missing_ips:
        raise DBMMcpBaseException(msg=_("部分 IP 未找到对应 proxy 实例: {}").format(sorted(missing_ips)))

    # 反查所有 proxy 实例承载的全部集群，用于校验输入集群是否完整
    related_cluster_ids = set()
    for pi in proxy_objs:
        for cluster in pi.cluster.all():
            related_cluster_ids.add(cluster.id)

    if related_cluster_ids != input_cluster_ids:
        extra = related_cluster_ids - input_cluster_ids
        missing_clusters = input_cluster_ids - related_cluster_ids
        raise DBMMcpBaseException(
            msg=_("输入集群与 proxy 机器承载集群不一致, 缺少={}, 多余={}").format(sorted(missing_clusters), sorted(extra))
        )

    # 按集群分组，生成 infos：每个集群一行，rebuild_proxy_hosts 为该集群的 proxy 实例列表
    infos_map: Dict[int, List[Dict[str, Any]]] = {}
    for pi in proxy_objs:
        host_info = {
            "ip": pi.machine.ip,
            "port": pi.port,
            "bk_biz_id": bk_biz_id,
            "bk_host_id": pi.machine.bk_host_id,
            "bk_cloud_id": bk_cloud_id,
        }
        for cluster in pi.cluster.all():
            if cluster.id in input_cluster_ids:
                infos_map.setdefault(cluster.id, []).append(host_info)

    infos = [
        {"cluster_id": cluster_id, "rebuild_proxy_hosts": hosts} for cluster_id, hosts in sorted(infos_map.items())
    ]

    ticket_param = {
        "ticket_type": TicketType.MYSQL_PROXY_REBUILD,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "remark": TicketType.MYSQL_PROXY_REBUILD,
        "details": {
            "infos": infos,
            "is_safe": True,
        },
    }

    slz = MysqlProxyRebuildDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.MYSQL_PROXY_REBUILD
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    def _fingerprint(infos):
        return tuple(
            sorted((info["cluster_id"], tuple(sorted(h["ip"] for h in info["rebuild_proxy_hosts"]))) for info in infos)
        )

    existing = find_duplicate_ticket(
        ticket_type=TicketType.MYSQL_PROXY_REBUILD,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(infos),
        fingerprint_of=lambda tk: _fingerprint(tk.details.get("infos", [])),
    )
    if existing:
        return existing

    return Ticket.create_ticket(**ticket_param)
