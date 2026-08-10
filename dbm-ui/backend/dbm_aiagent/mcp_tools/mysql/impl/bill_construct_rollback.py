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
import json
from datetime import datetime

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpBackupNotFoundException,
    DBMMcpBaseException,
    DBMMcpForbiddenException,
    DBMMcpNotSupportClusterTypeException,
)
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_backup_log import query_backup_log
from backend.dbm_aiagent.mcp_tools.mysql.impl.show_databases_with_patterns import show_databases_with_patterns
from backend.flow.consts import RollbackType
from backend.ticket.builders.common.constants import MySQLBackupSource, RollbackBuildClusterType
from backend.ticket.builders.mysql.mysql_fixpoint_rollback import MySQLFixPointRollbackDetailSerializer
from backend.ticket.builders.tendbcluster.tendb_fixpoint_rollback import TendbFixPointRollbackDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.time import datetime2str

# 集群类型 -> (有目标集群时的单据类型, 无目标集群时的单据类型) 映射
CLUSTER_TYPE_TICKET_MAP = {
    ClusterType.TenDBSingle.value: (TicketType.MYSQL_FIXPOINT_EXIST_CLUSTER, TicketType.MYSQL_ROLLBACK),
    ClusterType.TenDBHA.value: (TicketType.MYSQL_FIXPOINT_EXIST_CLUSTER, TicketType.MYSQL_ROLLBACK),
    ClusterType.TenDBCluster.value: (TicketType.TENDBCLUSTER_FIXPOINT_EXIST, TicketType.TENDBCLUSTER_ROLLBACK),
}


def _get_ticket_type(cluster_type: str, same_cluster: bool):
    """根据集群类型、源集群与目标集群是否相同判断单据类型"""
    if cluster_type not in CLUSTER_TYPE_TICKET_MAP:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_type)

    fixpoint_exist_cluster_ticket, rollback_ticket = CLUSTER_TYPE_TICKET_MAP[cluster_type]
    if same_cluster:
        return rollback_ticket, RollbackBuildClusterType.BUILD_INTO_METACLUSTER
    return fixpoint_exist_cluster_ticket, RollbackBuildClusterType.BUILD_INTO_EXIST_CLUSTER


def _get_rollback_type(rollback_time: datetime = None, backup_id: str = None) -> RollbackType:
    """根据参数确定回档方式"""
    if rollback_time:
        return RollbackType.REMOTE_AND_TIME
    if backup_id:
        return RollbackType.REMOTE_AND_BACKUPID
    raise DBMMcpBaseException("rollback_time or backup_id must be provided")


def check_cluster_ai_permission(cluster_obj: Cluster, ticket_type: TicketType):
    """校验集群是否有 AI 操作权限，以及该单据类型是否在允许列表中"""
    tag = cluster_obj.tags.filter(key="ai_permission").first()
    if not tag:
        raise DBMMcpForbiddenException()
    try:
        permission = json.loads(tag.value)
    except (json.JSONDecodeError, TypeError):
        raise DBMMcpForbiddenException()
    allowed_ticket_types = permission.get("ticket_type", [])

    if ticket_type.value not in allowed_ticket_types:
        raise DBMMcpForbiddenException()


@bill_response_wrapper
def bill_construct_rollback(
    bk_biz_id: int,
    username: str,
    cluster_domain: str,
    target_cluster_domain: str,
    databases: list,
    tables: list,
    rollback_time: datetime = None,
    backup_id: str = None,
) -> Ticket:
    """
    创建 MySQL/TENDBCLUSTER 数据构造到已有集群 / 回档原集群 单据

    参数：
        bk_biz_id: 业务ID
        username: 创建人用户名
        cluster_domain: 源集群域名
        target_cluster_domain: 目标集群域名
        databases: 需要构造的数据库
        tables: 需要构造的表
        rollback_time: 构造的时间点
        backup_id: 备份ID
    """
    cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    target_cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(
        bk_biz_id=bk_biz_id, immute_domain=target_cluster_domain
    )

    # 确定单据类型(构造还是回档）、回档类型（指定时间还是指定备份ID）
    ticket_type, rollback_cluster_type = _get_ticket_type(
        cluster_obj.cluster_type, bool(target_cluster_domain == cluster_domain)
    )

    check_cluster_ai_permission(target_cluster_obj, ticket_type)

    rollback_type = _get_rollback_type(rollback_time, backup_id)

    # 检查目标集群是否存在同名数据库
    affect_database_list = show_databases_with_patterns(target_cluster_domain, databases, []).get("databases")

    backup_results = query_backup_log(
        cluster_id=cluster_obj.pk,
        cluster_type=cluster_obj.cluster_type,
        backup_id=backup_id,
        rollback_time=rollback_time,
    )
    if not backup_results:
        raise DBMMcpBackupNotFoundException(
            msg=_("cluster_domain: {} cluster_type: {} backup_id: {} rollback_time: {}").format(
                cluster_domain, cluster_obj.cluster_type, backup_id, rollback_time
            )
        )

    ticket_param = {
        "ticket_type": ticket_type,
        "remark": ticket_type,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": {
            "rollback_cluster_type": rollback_cluster_type,
            "infos": [
                {
                    "cluster_id": cluster_obj.pk,
                    "target_cluster_id": target_cluster_obj.pk,
                    "databases": databases,
                    "tables": tables,
                    "databases_ignore": [],
                    "tables_ignore": [],
                    "backup_source": MySQLBackupSource.REMOTE.value,
                    "rollback_time": datetime2str(rollback_time) if rollback_time else None,
                    "rollback_type": rollback_type.value,
                    "backupinfo": backup_results[0],
                    "affect_database_list": affect_database_list,
                }
            ],
        },
    }

    slz_class = (
        MySQLFixPointRollbackDetailSerializer
        if cluster_obj.cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA]
        else TendbFixPointRollbackDetailSerializer
    )
    slz = slz_class(data=ticket_param["details"])
    slz.context["ticket_type"] = ticket_type
    slz.context["bk_biz_id"] = bk_biz_id
    slz.is_valid(raise_exception=True)

    return Ticket.create_ticket(**ticket_param)
