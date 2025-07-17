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

from backend.db_meta.models import StorageInstance
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.group_todo import GroupedTodo
from backend.db_periodic_task.local_tasks.mysql_autofix.exception import MySQLDBHAAutofixRemoteMultiClusters
from backend.db_services.dbbase.constants import IpSource
from backend.ticket.builders.common.base import HostRecycleSerializer
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


def remote_autofix(gtd: GroupedTodo, remotes: List[StorageInstance], dbas: List[str], resource_spec: dict) -> Ticket:
    # TenDBCluster 不存在集群间机器共享, gtd.cluster_ids 应该只有一个值
    if len(gtd.cluster_ids) > 1:
        raise MySQLDBHAAutofixRemoteMultiClusters(check_id=gtd.check_id, ip=gtd.ip, cluster_ids=gtd.cluster_ids)

    cluster_id = gtd.cluster_ids[0]

    tk = Ticket.create_ticket(
        ticket_type=TicketType.MYSQL_DBHA_AF_REMOTE_REPLACE,
        creator=dbas[0],
        helpers=dbas[1:],
        bk_biz_id=gtd.bk_biz_id,
        remark=TicketType.MYSQL_DBHA_AF_REMOTE_REPLACE,
        details={
            "bk_cloud_id": gtd.bk_cloud_id,
            "bk_biz_id": gtd.bk_biz_id,
            "disable_manual_confirm": True,
            "force": True,
            "backup_source": MySQLBackupSource.REMOTE,
            "ip_source": IpSource.RESOURCE_POOL,
            "ip_recycle": HostRecycleSerializer.DEFAULT,
            "infos": [
                {
                    "cluster_id": cluster_id,
                    "old_nodes": {
                        "old_slave": [
                            {
                                "bk_cloud_id": gtd.bk_cloud_id,
                                "ip": gtd.ip,
                                "bk_host_id": r.machine.bk_host_id,
                                "bk_biz_id": gtd.bk_biz_id,
                            }
                            for r in remotes
                        ]
                    },
                    "resource_spec": {
                        "new_slave": resource_spec,
                    },
                }
            ],
        },
    )

    return tk
