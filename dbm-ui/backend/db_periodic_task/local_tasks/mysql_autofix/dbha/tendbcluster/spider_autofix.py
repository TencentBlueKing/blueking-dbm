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
from backend.db_meta.enums import MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import Machine, ProxyInstance
from backend.db_monitor.constants import MonitorEventType
from backend.db_monitor.dataclass import BaseEventBody, MonitorEvent
from backend.db_monitor.models import MySQLDBHAAutofixTicketPriority, MySQLDBHAAutofixTicketStageQueue, MySQLDBHAEvent
from backend.db_services.dbbase.constants import IpSource
from backend.ticket.constants import TicketType


def replace_spider(cluster_ids: List[int], machine_type: MachineType, events: List[MySQLDBHAEvent]):
    """
    DBM 不允许 spider 机器在多集群共享
    spider 替换单据也不支持
    所以这里不考虑 len(cluster_ids) > 1 的情况
    """

    # Todo 理论上, 在events中ip应该是唯一的

    spider_master_events = []
    spider_slave_events = []
    for ev in events:
        spider_role = ProxyInstance.objects.get(machine__ip=ev.ip, port=ev.port).tendbclusterspiderext.spider_role
        if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
            spider_master_events.append(ev)
        elif spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE:
            spider_slave_events.append(ev)
        else:
            pass

    if spider_master_events:
        replace_spider_by_role(
            cluster_ids=cluster_ids,
            spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
            events=spider_master_events,
            priority=MySQLDBHAAutofixTicketPriority.P1,
        )

    if spider_slave_events:
        replace_spider_by_role(
            cluster_ids=cluster_ids,
            spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE,
            events=spider_slave_events,
            priority=MySQLDBHAAutofixTicketPriority.P3,
        )


def replace_spider_by_role(
    cluster_ids: List[int],
    spider_role: TenDBClusterSpiderRole,
    events: List[MySQLDBHAEvent],
    priority: MySQLDBHAAutofixTicketPriority,
):
    spec_ids = set()

    spider_old_ip_list = []
    for ev in events:
        m = Machine.objects.get(bk_cloud_id=ev.bk_cloud_id, ip=ev.ip)
        spider_old_ip_list.append(
            {
                "bk_cloud_id": ev.bk_cloud_id,
                "ip": ev.ip,
                "bk_host_id": m.bk_host_id,
                "bk_biz_id": ev.bk_biz_id,
                "port": ev.port,
            }
        )

    for p in ProxyInstance.objects.filter(cluster__pk__in=cluster_ids):
        spec_ids.add(p.machine.spec_id)

    if len(spec_ids) > 1:
        BKMonitorV3EventApi.send_event(
            events=[
                MonitorEvent(
                    event_name=MonitorEventType.MYSQL_DBHA_AUTOFIX_VALIDATE_FAILED,
                    target=f"{cluster_ids[0]}",
                    event=BaseEventBody(content=str(_("{} {} 规格不一致".format(events[0].immute_domain, spider_role)))),
                    dimension={
                        "appid": events[0].bk_biz_id,
                        "bk_cloud_id": events[0].bk_cloud_id,
                        "machine_type": MachineType.SPIDER.value,
                        "instance_role": spider_role,
                    },
                    timestamp=0,
                )
            ]
        )
        return

    infos = [
        {
            "cluster_id": cluster_ids[0],
            "resource_spec": {
                f"{spider_role}": {"spec_id": list(spec_ids)[0], "count": len(set([ev.ip for ev in events]))}
            },
            "spider_old_ip_list": spider_old_ip_list,
            "old_nodes": {"spider_old_ip_list": spider_old_ip_list},
            "switch_spider_role": spider_role,
        }
    ]

    dbas = events[0].dbas()
    queue_uuid = uuid.uuid4().__str__()
    ticket_param = {
        "ticket_type": TicketType.MYSQL_DBHA_AF_SPIDER_REPLACE,
        "remark": TicketType.MYSQL_DBHA_AF_SPIDER_REPLACE,
        "creator": dbas[0],
        "helpers": dbas[1:],
        "details": {
            "is_safe": False,
            "ip_source": IpSource.RESOURCE_POOL,
            "disable_manual_confirm": True,
            "infos": infos,
        },
        "bk_biz_id": events[0].bk_biz_id,
    }

    queue_to_create = []
    for ev in events:
        queue_to_create.append(
            MySQLDBHAAutofixTicketStageQueue(
                priority=priority,
                check_id=ev.check_id,
                cluster_id=ev.cluster_id,
                machine_type=MachineType.SPIDER.value,
                ticket_param=ticket_param,
                af_uuid=ev.af_uuid,
                queue_uuid=queue_uuid,
            )
        )

    MySQLDBHAAutofixTicketStageQueue.objects.bulk_create(queue_to_create)
