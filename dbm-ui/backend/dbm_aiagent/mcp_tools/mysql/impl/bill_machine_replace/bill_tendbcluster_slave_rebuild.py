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

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import StorageInstance
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import validate_clusters
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.tendbcluster.tendb_restore_local_slave import (
    TendbClusterRestoreLocalSlaveDetailSerializer,
)
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_tendbcluster_slave_rebuild(username: str, cluster_domains: List[str], ips: List[str]):
    """
    创建 TenDB Cluster Slave（remote slave）原地重建单据。

    - 每个 slave 实例（ip:port）一行，一行对应一个 remote slave 实例 + 所属集群；
    - 一台 remote 机器上可能存在多个分片的 slave 实例（不同端口），按实例展开；
    - creator 使用实际操作者（username），helpers 默认空。
    """
    cluster_objs, bk_biz_id, bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBCluster)
    input_cluster_ids = set(cluster_objs.values_list("id", flat=True))

    if not ips:
        raise DBMMcpBaseException(msg=_("ips 不能为空"))

    slave_objs = list(
        StorageInstance.objects.using(MYSQL_MCP_DB_READ)
        .filter(
            machine__ip__in=ips,
            machine__bk_cloud_id=bk_cloud_id,
            instance_inner_role=InstanceInnerRole.SLAVE,
            is_stand_by=True,
        )
        .select_related("machine")
        .prefetch_related("cluster")
    )

    found_ips = {si.machine.ip for si in slave_objs}
    missing_ips = set(ips) - found_ips
    if missing_ips:
        raise DBMMcpBaseException(msg=_("部分 IP 未找到对应 slave 实例: {}").format(sorted(missing_ips)))

    # 反查 slave 实例承载的集群并集，校验与输入集群一致（不多不少）
    related_cluster_ids = set()
    for si in slave_objs:
        for cluster in si.cluster.all():
            related_cluster_ids.add(cluster.id)

    if related_cluster_ids != input_cluster_ids:
        extra = related_cluster_ids - input_cluster_ids
        missing = input_cluster_ids - related_cluster_ids
        raise DBMMcpBaseException(msg=_("输入集群与 slave 实例承载集群不一致, 缺少={}, 多余={}").format(sorted(missing), sorted(extra)))

    infos: List[Dict[str, Any]] = []
    for si in slave_objs:
        for cluster in si.cluster.all():
            if cluster.id in input_cluster_ids:
                infos.append(
                    {
                        "slave": {
                            "ip": si.machine.ip,
                            "port": si.port,
                            "bk_biz_id": bk_biz_id,
                            "bk_host_id": si.machine.bk_host_id,
                            "bk_cloud_id": bk_cloud_id,
                        },
                        "cluster_id": cluster.id,
                    }
                )

    infos.sort(key=lambda x: (x["cluster_id"], x["slave"]["ip"], x["slave"]["port"]))

    ticket_param = {
        "ticket_type": TicketType.TENDBCLUSTER_RESTORE_LOCAL_SLAVE,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "remark": TicketType.TENDBCLUSTER_RESTORE_LOCAL_SLAVE,
        "details": {
            "force": False,
            "backup_source": MySQLBackupSource.REMOTE,
            "infos": infos,
        },
    }

    slz = TendbClusterRestoreLocalSlaveDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.TENDBCLUSTER_RESTORE_LOCAL_SLAVE
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    def _fingerprint(infos):
        return tuple(sorted((info["cluster_id"], info["slave"]["ip"], info["slave"]["port"]) for info in infos))

    existing = find_duplicate_ticket(
        ticket_type=TicketType.TENDBCLUSTER_RESTORE_LOCAL_SLAVE,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(infos),
        fingerprint_of=lambda tk: _fingerprint(tk.details.get("infos", [])),
    )
    if existing:
        return existing

    return Ticket.create_ticket(**ticket_param)
