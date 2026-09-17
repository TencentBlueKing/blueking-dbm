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
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpNotSupportClusterTypeException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.flow.consts import MySQLBackupFileTagEnum, MySQLBackupTypeEnum
from backend.ticket.builders.mysql.mysql_full_backup import MySQLFullBackupDetailSerializer
from backend.ticket.builders.tendbcluster.full_backup import TenDBClusterFullBackUpDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def mysql_full_backup(
    bk_biz_id: int,
    username: str,
    cluster_domains: List[str],
    backup_type: str = MySQLBackupTypeEnum.PHYSICAL.value,
    backup_local: str = InstanceInnerRole.SLAVE.value,
) -> Ticket:
    cluster_objs = list(
        Cluster.objects.using(MYSQL_MCP_DB_READ).filter(bk_biz_id=bk_biz_id, immute_domain__in=cluster_domains)
    )

    found_domains = {c.immute_domain for c in cluster_objs}
    missing_domains = set(cluster_domains) - found_domains
    if missing_domains:
        raise DBMMcpBaseException(msg="部分集群未找到: {}".format(sorted(missing_domains)))

    cluster_type_set = {c.cluster_type for c in cluster_objs}
    if len(cluster_type_set) > 1:
        raise DBMMcpBaseException(msg="不允许混合集群类型: {}".format(sorted(cluster_type_set)))
    elif cluster_type_set == {ClusterType.TenDBCluster.value}:
        ticket_type = TicketType.TENDBCLUSTER_FULL_BACKUP
    elif cluster_type_set == {ClusterType.TenDBHA.value}:
        ticket_type = TicketType.MYSQL_HA_FULL_BACKUP
    else:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=sorted(cluster_type_set))

    ticket_param = {
        "ticket_type": ticket_type,
        "remark": ticket_type,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": {
            "backup_type": backup_type,
            "file_tag": MySQLBackupFileTagEnum.DBFILE1M,
            "infos": [
                {
                    "cluster_id": cluster_obj.pk,
                    "backup_local": backup_local,
                }
                for cluster_obj in cluster_objs
            ],
        },
    }

    if ticket_type == TicketType.MYSQL_HA_FULL_BACKUP:
        slz = MySQLFullBackupDetailSerializer(data=ticket_param["details"])
    else:
        slz = TenDBClusterFullBackUpDetailSerializer(data=ticket_param["details"])

    slz.context["bk_biz_id"] = bk_biz_id
    slz.context["ticket_type"] = ticket_type

    slz.is_valid(raise_exception=True)

    def _fingerprint(details):
        infos = details.get("infos", [])
        cluster_ids = tuple(sorted(info["cluster_id"] for info in infos))
        backup_locals = tuple(sorted(info.get("backup_local") for info in infos))
        return (cluster_ids, details.get("backup_type"), backup_locals)

    existing = find_duplicate_ticket(
        ticket_type=ticket_type,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(ticket_param["details"]),
        fingerprint_of=lambda tk: _fingerprint(tk.details),
    )
    if existing:
        return existing

    return Ticket.create_ticket(**ticket_param)
