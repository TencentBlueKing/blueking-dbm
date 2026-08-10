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

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Machine, StorageInstance
from backend.db_services.dbbase.constants import IpSource, SourceType
from backend.dbm_aiagent.mcp_tools.decorators import bill_response_wrapper
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.helper import (
    check_clusters_consistency,
    validate_clusters,
)
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.builders.tendbcluster.tendb_restore_slave import TendbClusterRestoreSlaveDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_remote_replace(cluster_domain: str, ips: List[str]):
    cluster_objs, bk_biz_id, bk_cloud_id = validate_clusters([cluster_domain], ClusterType.TenDBCluster)

    remote_slave_objs = StorageInstance.objects.using(MYSQL_MCP_DB_READ).filter(
        machine__ip__in=ips, machine__bk_cloud_id=bk_cloud_id, instance_inner_role=InstanceInnerRole.SLAVE
    )

    check_clusters_consistency(cluster_objs, ips, remote_slave_objs)

    dbas = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.TenDBCluster)

    infos = []

    for ip in ips:
        machine_obj = Machine.objects.using(MYSQL_MCP_DB_READ).get(bk_cloud_id=bk_cloud_id, ip=ip)
        slave_info = {
            "bk_biz_id": bk_biz_id,
            "bk_cloud_id": bk_cloud_id,
            "bk_host_id": machine_obj.bk_host_id,
            "ip": ip,
            "port": 0,
        }
        spec_id = machine_obj.spec_id

        infos.append(
            {
                "old_nodes": {
                    "old_slave": [slave_info],
                },
                "resource_spec": {"new_slave": {"count": 1, "spec_id": spec_id}},
                "cluster_id": cluster_objs[0].id,
            }
        )

    ticket_param = {
        "ticket_type": TicketType.TENDBCLUSTER_RESTORE_SLAVE,
        "creator": dbas[0],
        "helpers": dbas[1:],
        "bk_biz_id": bk_biz_id,
        "remark": TicketType.TENDBCLUSTER_RESTORE_SLAVE,
        "details": {
            "bk_cloud_id": bk_cloud_id,
            "bk_biz_id": bk_biz_id,
            "backup_source": MySQLBackupSource.REMOTE,  # MySQLBackupSource.REMOTE,
            "ip_source": IpSource.RESOURCE_POOL,
            "source_type": SourceType.RESOURCE_AUTO,
            "disable_manual_confirm": False,
            "infos": infos,
        },
    }

    slz = TendbClusterRestoreSlaveDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.TENDBCLUSTER_RESTORE_SLAVE
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    return Ticket.create_ticket(**ticket_param)
