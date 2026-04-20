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
from backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_backup_log import query_backup_log
from backend.flow.consts import RollbackType
from backend.ticket.builders.common.constants import MySQLBackupSource, RollbackBuildClusterType
from backend.ticket.builders.mysql.mysql_fixpoint_rollback import MySQLFixPointRollbackDetailSerializer
from backend.ticket.builders.tendbcluster.tendb_fixpoint_rollback import TendbFixPointRollbackDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.time import datetime2str


@bill_response_wrapper
def bill_fixpoint_exist_cluster(
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
    创建 MySQL/TENDBCLUSTER 数据构造到已有集群单据

    参数：
        bk_biz_id: 业务ID
        username: 创建人用户名
        cluster_domain: 集群域名
        target_cluster_domain: 目标集群域名
        databases: 需要构造的数据库
        tables: 需要构造的表
        rollback_time: 构造的时间点
        backup_id: 备份ID
    """
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    target_cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=target_cluster_domain)

    if cluster_obj.cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA]:
        ticket_type = TicketType.MYSQL_FIXPOINT_EXIST_CLUSTER
    elif cluster_obj.cluster_type == ClusterType.TenDBCluster:
        ticket_type = TicketType.TENDBCLUSTER_FIXPOINT_EXIST
    else:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_obj.cluster_type)

    if not target_cluster_obj.tags.filter(key="test_rollback").exists():
        raise DBMMcpForbiddenException()

    if rollback_time:
        rollback_type = RollbackType.REMOTE_AND_TIME
    elif backup_id:
        rollback_type = RollbackType.REMOTE_AND_BACKUPID
    else:
        raise DBMMcpBaseException("rollback_time or backup_id must be provided")
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
    backup_info = backup_results[0]
    ticket_param = {
        "ticket_type": ticket_type,
        "remark": ticket_type,
        "creator": username,
        "helpers": [],
        "bk_biz_id": bk_biz_id,
        "details": {
            "rollback_cluster_type": RollbackBuildClusterType.BUILD_INTO_EXIST_CLUSTER,
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
                    "backupinfo": backup_info,
                }
            ],
        },
    }

    if ticket_type == TicketType.MYSQL_FIXPOINT_EXIST_CLUSTER:
        slz = MySQLFixPointRollbackDetailSerializer(data=ticket_param["details"])
    else:
        slz = TendbFixPointRollbackDetailSerializer(data=ticket_param["details"])

    slz.context["ticket_type"] = ticket_type
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    return Ticket.create_ticket(**ticket_param)
