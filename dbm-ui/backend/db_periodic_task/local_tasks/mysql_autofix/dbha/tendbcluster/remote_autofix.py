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
import uuid
from typing import List

from backend.db_meta.enums import MachineType
from backend.db_meta.models import Machine
from backend.db_monitor.models import MySQLDBHAAutofixTicketPriority, MySQLDBHAAutofixTicketStageQueue, MySQLDBHAEvent
from backend.db_services.dbbase.constants import IpSource, SourceType
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.constants import TicketType


def replace_remote(cluster_ids: List[int], machine_type: MachineType, events: List[MySQLDBHAEvent]):
    """
    可能会有多台机器
    一股脑一单重建就完事了
    """
    bk_cloud_id = events[0].bk_cloud_id
    cluster_id = cluster_ids[0]  # 集群 id 必然只有 1 个
    ips = list({ev.ip for ev in events})

    infos = []
    for ip in ips:
        machine_obj = Machine.objects.get(bk_cloud_id=bk_cloud_id, ip=ip)
        ip_events = [ev for ev in events if ev.ip == ip]
        info = {
            "old_nodes": {"old_slave": []},
            "resource_spec": {"new_slave": {"count": 1, "spec_id": machine_obj.spec_id}},
            "cluster_id": cluster_id,
        }

        old_slaves = []
        for ev in ip_events:
            old_slaves.append(
                {
                    "bk_biz_id": ev.bk_biz_id,
                    "bk_cloud_id": bk_cloud_id,
                    "bk_host_id": machine_obj.bk_host_id,
                    "ip": ev.ip,
                    # "port": ev.port
                }
            )

        info["old_nodes"]["old_slave"] = old_slaves
        infos.append(info)

    dbas = events[0].dbas()
    queue_uuid = uuid.uuid4().__str__()
    ticket_param = {
        "ticket_type": TicketType.MYSQL_DBHA_AF_REMOTE_REPLACE,
        "creator": dbas[0],
        "helpers": dbas[1:],
        "bk_biz_id": events[0].bk_biz_id,
        "remark": TicketType.MYSQL_DBHA_AF_REMOTE_REPLACE,
        "details": {
            "bk_cloud_id": events[0].bk_cloud_id,
            "bk_biz_id": events[0].bk_biz_id,
            "backup_source": MySQLBackupSource.REMOTE,
            "ip_source": IpSource.RESOURCE_POOL,
            "source_type": SourceType.RESOURCE_AUTO,
            "disable_manual_confirm": True,
            "infos": infos,
        },
    }

    queue_to_create = []
    for ev in events:
        queue_to_create.append(
            MySQLDBHAAutofixTicketStageQueue(
                priority=MySQLDBHAAutofixTicketPriority.P2,
                check_id=ev.check_id,
                cluster_id=ev.cluster_id,
                machine_type=machine_type,
                ticket_param=ticket_param,
                af_uuid=ev.af_uuid,
                queue_uuid=queue_uuid,
            )
        )

    MySQLDBHAAutofixTicketStageQueue.objects.bulk_create(queue_to_create)
