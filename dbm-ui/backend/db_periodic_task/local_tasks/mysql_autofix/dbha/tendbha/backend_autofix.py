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
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import InstanceInnerRole, InstancePhase, MachineType
from backend.db_meta.models import StorageInstance
from backend.db_monitor.models import MySQLAutofixTicketStatus, MySQLDBHAAutofixTodo
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.group_todo import GroupedTodo
from backend.db_periodic_task.local_tasks.mysql_autofix.exception import MySQLDBHAAutofixBadInstanceStatus
from backend.db_services.dbbase.constants import IpSource
from backend.flow.consts import InstanceStatus
from backend.ticket.builders.common.base import HostRecycleSerializer
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


def backend_autofix(gtd: GroupedTodo):
    records = MySQLDBHAAutofixTodo.objects.filter(check_id=gtd.check_id)

    backends = list(
        StorageInstance.objects.filter(
            machine__ip=gtd.ip,
            machine__bk_cloud_id=gtd.bk_cloud_id,
            status=InstanceStatus.UNAVAILABLE,
            phase=InstancePhase.ONLINE,
            machine_type=MachineType.BACKEND,
            instance_inner_role=InstanceInnerRole.SLAVE,
            is_stand_by=True,
        ).prefetch_related("machine")
    )
    if len(backends) != records.count():
        raise MySQLDBHAAutofixBadInstanceStatus(machine_type=gtd.machine_type, ip=gtd.ip)

    dbas = DBAdministrator.get_biz_db_type_admins(bk_biz_id=gtd.bk_biz_id, db_type=DBType.MySQL.value)

    tk = Ticket.create_ticket(
        ticket_type=TicketType.MYSQL_DBHA_AF_BACKEND_REPLACE,
        creator=dbas[0],
        helpers=dbas[1:],
        bk_biz_id=gtd.bk_biz_id,
        remark=TicketType.MYSQL_DBHA_AF_BACKEND_REPLACE,
        details={
            "bk_cloud_id": gtd.bk_cloud_id,
            "bk_biz_id": gtd.bk_biz_id,
            "disable_manual_confirm": True,
            "disable_manual_confirm" "force": True,
            "backup_source": MySQLBackupSource.REMOTE,
            "ip_source": IpSource.RESOURCE_POOL,
            "ip_recycle": HostRecycleSerializer.DEFAULT,
            "infos": [
                {
                    "cluster_ids": gtd.cluster_ids,
                    "old_nodes": {
                        "old_slave": [
                            {
                                "bk_cloud_id": gtd.bk_cloud_id,
                                "ip": gtd.ip,
                                "bk_host_id": b.machine.bk_host_id,
                                "bk_biz_id": gtd.bk_biz_id,
                            }
                            for b in backends
                        ]
                    },
                    "resource_spec": {
                        "new_slave": {
                            "count": 1,
                            "spec_id": backends[0].machine.spec_id,
                        }
                    },
                }
            ],
        },
    )
    MySQLDBHAAutofixTodo.objects.filter(check_id=gtd.check_id).update(
        ticket_id=tk.id, status=MySQLAutofixTicketStatus.PENDING
    )
