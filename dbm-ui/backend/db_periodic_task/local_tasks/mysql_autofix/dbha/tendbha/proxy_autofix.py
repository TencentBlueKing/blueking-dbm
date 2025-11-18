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
from backend.ticket.builders.common.base import HostRecycleSerializer
from backend.ticket.builders.common.constants import OperaObjType
from backend.ticket.constants import TicketType


def replace_proxy(cluster_ids: List[int], machine_type: MachineType, events: List[MySQLDBHAEvent]):
    """
    机器数量可能不止一台了
    """
    spec_ids = set()

    proxy_infos = []
    for ev in events:
        m = Machine.objects.get(bk_cloud_id=ev.bk_cloud_id, ip=ev.ip)
        d = {
            "bk_biz_id": ev.bk_biz_id,
            "bk_cloud_id": ev.bk_cloud_id,
            "bk_host_id": m.bk_host_id,
            "ip": ev.ip,
            "port": ev.port,
        }
        proxy_infos.append(d)
        spec_ids.add(m.spec_id)

    # ToDo
    if len(spec_ids) > 1:
        raise

    resource_spec = {"spec_id": list(spec_ids)[0], "count": len(set([ev.ip for ev in events]))}

    dbas = events[0].dbas()
    queue_uuid = uuid.uuid4().__str__()
    ticket_param = {
        "ticket_type": TicketType.MYSQL_DBHA_AF_PROXY_REPLACE,
        "remark": TicketType.MYSQL_DBHA_AF_PROXY_REPLACE,
        # "ignore_duplication": True,
        "creator": dbas[0],
        "helpers": dbas[1:],
        "details": {
            "is_safe": False,
            "ip_source": IpSource.RESOURCE_POOL,
            "source_type": SourceType.RESOURCE_AUTO,
            "ip_recycle": HostRecycleSerializer.DEFAULT,
            "force": True,
            "infos": [
                {
                    "old_nodes": {"origin_proxy": proxy_infos},
                    # "origin_proxy": proxy_infos,
                    "resource_spec": {"target_proxy": resource_spec},
                    "cluster_ids": cluster_ids,
                }
            ],
            "opera_object": OperaObjType.MACHINE,
            "disable_manual_confirm": True,
        },
        "bk_biz_id": events[0].bk_biz_id,
    }

    queue_to_create = []
    for ev in events:
        queue_to_create.append(
            MySQLDBHAAutofixTicketStageQueue(
                priority=MySQLDBHAAutofixTicketPriority.P1.value,
                check_id=ev.check_id,
                cluster_id=ev.cluster_id,
                machine_type=machine_type.value,
                ticket_param=ticket_param,
                af_uuid=ev.af_uuid,
                queue_uuid=queue_uuid,
            )
        )

    MySQLDBHAAutofixTicketStageQueue.objects.bulk_create(queue_to_create)
