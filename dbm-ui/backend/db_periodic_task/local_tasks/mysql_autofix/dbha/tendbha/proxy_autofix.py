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

from django.utils.translation import gettext_lazy as _

from backend.components.bkmonitorv3.client import BKMonitorV3EventApi
from backend.db_meta.enums import MachineType
from backend.db_meta.models import Machine, ProxyInstance
from backend.db_monitor.constants import MonitorEventType
from backend.db_monitor.dataclass import BaseEventBody, MonitorEvent
from backend.db_monitor.models import MySQLDBHAAutofixTicketPriority, MySQLDBHAAutofixTicketStageQueue, MySQLDBHAEvent
from backend.db_services.dbbase.constants import IpSource
from backend.ticket.constants import TicketType


def replace_proxy(cluster_ids: List[int], machine_type: MachineType, events: List[MySQLDBHAEvent]):
    """
    机器数量可能不止一台了
    其实仔细想想这里不太可能出现大于一台的机器
    因为一个集群就两台 proxy
    第二台机器故障是不触发 DBHA 的
    """
    spec_ids = set()

    proxy_infos = []
    # proxy 替换协议的这个 field 实际是机器级别
    for (bk_cloud_id, ip) in {(ev.bk_cloud_id, ev.ip) for ev in events}:
        # for ev in events:
        m = Machine.objects.get(bk_cloud_id=bk_cloud_id, ip=ip)
        d = {"bk_cloud_id": bk_cloud_id, "ip": ip, "bk_host_id": m.bk_host_id, "bk_biz_id": m.bk_biz_id, "port": 0}
        proxy_infos.append(d)

    # 统计相关集群所有 proxy 的 spec id
    for p in ProxyInstance.objects.filter(cluster__pk__in=cluster_ids):
        spec_ids.add(p.machine.spec_id)

    # 从上面 docstring 的分析
    # 这里都假定只有一台机器得了, 告警信息就发一台的
    if len(spec_ids) > 1:
        BKMonitorV3EventApi.send_event(
            events=[
                MonitorEvent(
                    event_name=MonitorEventType.MYSQL_DBHA_AUTOFIX_VALIDATE_FAILED,
                    target=f"{events[0].ip}",
                    event=BaseEventBody(content=str(_("{} 所属集群 proxy 规格不一致".format(events[0].ip)))),
                    dimension={
                        "appid": events[0].bk_biz_id,
                        "bk_cloud_id": events[0].bk_cloud_id,
                        "machine_type": machine_type,
                        "instance_role": events[0].instance_role,
                        "ip": events[0].ip,
                        "port": events[0].port,
                    },
                    timestamp=0,
                )
            ]
        )
        # 不能瞎 raise, 有可能会中断其他的自愈
        return

    resource_spec = {"spec_id": list(spec_ids)[0], "count": len(set([ev.ip for ev in events]))}

    dbas = events[0].dbas()
    queue_uuid = uuid.uuid4().__str__()
    ticket_param = {
        "ticket_type": TicketType.MYSQL_DBHA_AF_PROXY_REPLACE,
        "remark": TicketType.MYSQL_DBHA_AF_PROXY_REPLACE,
        "creator": dbas[0],
        "helpers": dbas[1:],
        "details": {
            "is_safe": False,
            "ip_source": IpSource.RESOURCE_POOL,
            "infos": [
                {
                    "cluster_ids": cluster_ids,
                    "origin_proxies": proxy_infos,
                    "old_nodes": {
                        "proxy": proxy_infos,
                    },
                    "resource_spec": {"target_proxies": resource_spec},
                }
            ],
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
