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

from backend.db_meta.enums import InstancePhase, InstanceStatus, MachineType
from backend.db_meta.models import Cluster, ProxyInstance
from backend.db_monitor.models import MySQLAutofixTicketStatus, MySQLAutofixTodo
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.group_todo import GroupedTodo
from backend.db_periodic_task.local_tasks.mysql_autofix.exception import (
    MySQLDBHAAutofixBadInstanceStatus,
    MySQLDBHAAutofixSpiderMultiClusters,
)
from backend.db_services.dbbase.constants import IpSource
from backend.ticket.builders.common.base import HostRecycleSerializer
from backend.ticket.builders.common.constants import ShrinkType
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


def spider_autofix(gtd: GroupedTodo):
    """
    1. 踢除故障 spider, 自动过单, 自动执行
    2. 提一个扩容单, 自动过单, 人工执行
    代码顺序实现为先生成扩容, 再踢除. 会比较好写
    """
    records = MySQLAutofixTodo.objects.filter(check_id=gtd.check_id)

    proxies = list(
        ProxyInstance.objects.filter(
            machine__ip=gtd.ip,
            machine__bk_cloud_id=gtd.bk_cloud_id,
            status=InstanceStatus.UNAVAILABLE,
            phase=InstancePhase.ONLINE,
            machine_type=MachineType.SPIDER,
        ).prefetch_related("machine")
    )
    if len(proxies) != records.count():
        raise MySQLDBHAAutofixBadInstanceStatus(machine_type=gtd.machine_type, ip=gtd.ip)

    if len(gtd.cluster_ids) > 1:
        raise MySQLDBHAAutofixSpiderMultiClusters(check_id=gtd.check_id, ip=gtd.ip, cluster_ids=gtd.cluster_ids)

    cluster_id = gtd.cluster_ids[0]
    cluster_obj = Cluster.objects.get(pk=cluster_id)

    # 自动审核, 人工执行, 不跟踪状态
    Ticket.create_ticket(
        ticket_type=TicketType.MYSQL_DBHA_AUTOFIX_SPIDER_ADD,
        creator="system",
        bk_biz_id=gtd.bk_biz_id,
        remark=TicketType.MYSQL_DBHA_AUTOFIX_SPIDER_ADD,
        details={
            "bk_cloud_id": gtd.bk_cloud_id,
            "bk_biz_id": gtd.bk_biz_id,
            "ip_source": IpSource.RESOURCE_POOL,
            "infos": [
                {
                    "cluster_id": cluster_id,
                    "add_spider_role": proxies[0].tendbclusterspiderext.spider_role,
                    "resource_spec": {
                        "spider": {
                            "spec_id": proxies[0].machine.spec_id,
                            "count": 1,
                            "location_spec": {
                                "city": cluster_obj.region,
                                "sub_zone_ids": [proxies[0].machine.bk_sub_zone_id],
                            },
                        }
                    },
                }
            ],
        },
    )

    tk = Ticket.create_ticket(
        ticket_type=TicketType.MYSQL_DBHA_AUTOFIX_SPIDER_REDUCE,
        creator="system",
        bk_biz_id=gtd.bk_biz_id,
        remark=TicketType.MYSQL_DBHA_AUTOFIX_SPIDER_REDUCE,
        details={
            "bk_cloud_id": gtd.bk_cloud_id,
            "bk_biz_id": gtd.bk_biz_id,
            "is_safe": False,
            "ip_recycle": HostRecycleSerializer.DEFAULT,
            "shrink_type": ShrinkType.HOST,
            "infos": [
                {
                    "cluster_id": cluster_id,
                    "old_nodes": {
                        "spider_reduced_hosts": [
                            {
                                "bk_cloud_id": gtd.bk_cloud_id,
                                "ip": gtd.ip,
                                "bk_host_id": p.machine.bk_host_id,
                                "bk_biz_id": gtd.bk_biz_id,
                                "port": p.port,
                            }
                            for p in proxies
                        ]
                    },
                    "reduce_spider_role": proxies[0].tendbclusterspiderext.spider_role,
                }
            ],
        },
    )
    MySQLAutofixTodo.objects.filter(check_id=gtd.check_id).update(
        ticket_id=tk.id,
        status=MySQLAutofixTicketStatus.PENDING,
    )
