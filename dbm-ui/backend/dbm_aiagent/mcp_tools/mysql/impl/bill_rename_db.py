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
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpNotSupportClusterTypeException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.ticket.builders.mysql.mysql_rename_database import MySQLRenameDatabaseSerializer
from backend.ticket.builders.tendbcluster.tendb_rename import TendbRenameSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_rename_db(
    bk_biz_id: int, username: str, cluster_domain: str, source_dbname: str, target_dbname: str
) -> Ticket:
    cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    if cluster_obj.cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA]:
        ticket_type = TicketType.MYSQL_RENAME_DATABASE
    elif cluster_obj.cluster_type == ClusterType.TenDBCluster:
        ticket_type = TicketType.TENDBCLUSTER_RENAME_DATABASE
    else:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_obj.cluster_type)

    ticket_param = {
        "ticket_type": ticket_type,
        "remark": ticket_type,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": {
            "force": True,
            "infos": [{"cluster_id": cluster_obj.pk, "from_database": source_dbname, "to_database": target_dbname}],
        },
    }

    if ticket_type == TicketType.MYSQL_RENAME_DATABASE:
        slz = MySQLRenameDatabaseSerializer(data=ticket_param["details"])
    else:
        slz = TendbRenameSerializer(data=ticket_param["details"])

    slz.context["ticket_type"] = ticket_type
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    return Ticket.create_ticket(**ticket_param)
