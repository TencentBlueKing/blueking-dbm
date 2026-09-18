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
from typing import List

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.flow.consts import MySQLBackupFileTagEnum, MySQLBackupTypeEnum
from backend.ticket.builders.tendbcluster.full_backup import TenDBClusterFullBackUpDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_tendbcluster_fullbackup(
    bk_biz_id: int,
    username: str,
    cluster_domains: List[str],
    backup_type: str = MySQLBackupTypeEnum.PHYSICAL.value,
    backup_local: str = InstanceInnerRole.SLAVE.value,
) -> Ticket:
    """
    创建 TenDB Cluster 全库备份单据。

    - 默认物理备份（physical）；
    - 默认在 RemoteDR（remote slave，backup_local=slave）上备份；
    - 保存时间固定 1 个月（DBFILE1M）；
    - 支持一次传入多个集群（需同为 TenDBCluster 类型）。
    """
    if not cluster_domains:
        raise DBMMcpBaseException(msg="cluster_domains 不能为空")

    cluster_objs = list(
        Cluster.objects.using(MYSQL_MCP_DB_READ).filter(
            bk_biz_id=bk_biz_id, immute_domain__in=cluster_domains, cluster_type=ClusterType.TenDBCluster.value
        )
    )

    found_domains = {c.immute_domain for c in cluster_objs}
    missing_domains = set(cluster_domains) - found_domains
    if missing_domains:
        raise DBMMcpBaseException(msg="部分集群未找到或非 TenDBCluster 类型: {}".format(sorted(missing_domains)))

    ticket_param = {
        "ticket_type": TicketType.TENDBCLUSTER_FULL_BACKUP,
        "remark": TicketType.TENDBCLUSTER_FULL_BACKUP,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": {
            "backup_type": backup_type,
            "file_tag": MySQLBackupFileTagEnum.DBFILE1M,
            "infos": [{"cluster_id": cluster_obj.pk, "backup_local": backup_local} for cluster_obj in cluster_objs],
        },
    }

    slz = TenDBClusterFullBackUpDetailSerializer(data=ticket_param["details"])
    slz.context["bk_biz_id"] = bk_biz_id
    slz.context["ticket_type"] = TicketType.TENDBCLUSTER_FULL_BACKUP

    slz.is_valid(raise_exception=True)

    def _fingerprint(details):
        """幂等指纹：cluster_id 集合 + backup_type + backup_local，避免不同类型/位置的备份互相复用"""
        infos = details.get("infos", [])
        cluster_ids = tuple(sorted(info["cluster_id"] for info in infos))
        backup_locals = tuple(sorted(info.get("backup_local") for info in infos))
        return (cluster_ids, details.get("backup_type"), backup_locals)

    existing = find_duplicate_ticket(
        ticket_type=TicketType.TENDBCLUSTER_FULL_BACKUP,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(ticket_param["details"]),
        fingerprint_of=lambda tk: _fingerprint(tk.details),
    )
    if existing:
        return existing

    return Ticket.create_ticket(**ticket_param)
