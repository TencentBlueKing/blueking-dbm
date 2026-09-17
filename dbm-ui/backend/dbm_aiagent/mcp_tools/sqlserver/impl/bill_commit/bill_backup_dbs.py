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

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpNotSupportClusterTypeException
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.flow.consts import SqlserverBackupFileTagEnum, SqlserverBackupMode
from backend.ticket.builders.sqlserver.sqlserver_backup import SQLServerBackupDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_sqlserver_backup_dbs(
    username: str,
    bk_biz_id: int,
    cluster_domain: str,
    backup_dbs: List[str],
    file_tag: str = SqlserverBackupFileTagEnum.DBFILE1M.value,
    backup_type: str = SqlserverBackupMode.FULL_BACKUP.value,
    backup_place: str = InstanceInnerRole.MASTER.value,
) -> Ticket:
    """创建 SQLServer 库表备份单据。"""
    cluster = Cluster.objects.filter(bk_biz_id=bk_biz_id, immute_domain=cluster_domain).first()
    if not cluster:
        raise DBMMcpBaseException(msg=_("未找到集群: {}").format(cluster_domain))

    if cluster.cluster_type not in [ClusterType.SqlserverHA.value, ClusterType.SqlserverSingle.value]:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster.cluster_type)

    ticket_param = {
        "ticket_type": TicketType.SQLSERVER_BACKUP_DBS,
        "remark": TicketType.SQLSERVER_BACKUP_DBS,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": {
            "backup_place": backup_place,
            "backup_type": backup_type,
            "file_tag": file_tag,
            "infos": [
                {
                    "cluster_id": cluster.pk,
                    "backup_dbs": backup_dbs,
                    "db_list": [],
                    "ignore_db_list": [],
                }
            ],
        },
    }

    slz = SQLServerBackupDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.SQLSERVER_BACKUP_DBS
    slz.context["bk_biz_id"] = bk_biz_id
    slz.is_valid(raise_exception=True)

    def _fingerprint(details):
        return (
            details.get("backup_place"),
            details.get("backup_type"),
            details.get("file_tag"),
            tuple(
                sorted(
                    (info["cluster_id"], tuple(sorted(info.get("backup_dbs") or [])))
                    for info in details.get("infos", [])
                )
            ),
        )

    existing = find_duplicate_ticket(
        ticket_type=TicketType.SQLSERVER_BACKUP_DBS,
        creator=username,
        bk_biz_id=bk_biz_id,
        target_fingerprint=_fingerprint(ticket_param["details"]),
        fingerprint_of=lambda tk: _fingerprint(tk.details),
    )
    if existing:
        return existing

    return Ticket.create_ticket(**ticket_param)
