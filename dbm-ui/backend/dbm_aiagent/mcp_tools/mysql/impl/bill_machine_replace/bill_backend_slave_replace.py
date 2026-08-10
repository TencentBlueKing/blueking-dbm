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
from backend.ticket.builders.mysql.mysql_restore_slave import MysqlRestoreSlaveDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@bill_response_wrapper
def bill_backend_slave_replace(cluster_domains: List[str], ips: List[str]):
    cluster_objs, bk_biz_id, bk_cloud_id = validate_clusters(cluster_domains, ClusterType.TenDBHA)

    slave_objs = StorageInstance.objects.using(MYSQL_MCP_DB_READ).filter(
        machine__ip__in=ips, machine__bk_cloud_id=bk_cloud_id, instance_inner_role=InstanceInnerRole.SLAVE
    )

    check_clusters_consistency(cluster_objs, ips, slave_objs)

    machine_objs = Machine.objects.using(MYSQL_MCP_DB_READ).filter(bk_cloud_id=bk_cloud_id, ip__in=ips)
    spec_ids = list(set(machine_objs.values_list("spec_id", flat=True)))
    if len(spec_ids) > 1:
        raise

    info: Dict[str, Any] = {
        "old_nodes": {
            "old_slave": [
                {
                    "bk_biz_id": bk_biz_id,
                    "bk_cloud_id": bk_cloud_id,
                    "bk_host_id": m.bk_host_id,
                    "ip": m.ip,
                }
                for m in machine_objs
            ]
        },
        "resource_spec": {
            "new_slave": {
                "count": len(ips),
                "spec_id": spec_ids[0],
            }
        },
        "cluster_ids": list(cluster_objs.values_list("id", flat=True)),
    }

    dbas = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.MySQL)

    ticket_param = {
        "ticket_type": TicketType.MYSQL_RESTORE_SLAVE,
        "creator": dbas[0],
        "helpers": dbas[1:],
        "bk_biz_id": bk_biz_id,
        "remark": TicketType.MYSQL_RESTORE_SLAVE,
        "details": {
            "bk_cloud_id": bk_cloud_id,
            "bk_biz_id": bk_biz_id,
            "backup_source": MySQLBackupSource.REMOTE,
            "ip_source": IpSource.RESOURCE_POOL,
            "source_type": SourceType.RESOURCE_AUTO,
            "disable_manual_confirm": False,
            "infos": [info],
        },
    }

    slz = MysqlRestoreSlaveDetailSerializer(data=ticket_param["details"])
    slz.context["ticket_type"] = TicketType.MYSQL_RESTORE_SLAVE
    slz.context["bk_biz_id"] = bk_biz_id

    slz.is_valid(raise_exception=True)

    return Ticket.create_ticket(**ticket_param)
