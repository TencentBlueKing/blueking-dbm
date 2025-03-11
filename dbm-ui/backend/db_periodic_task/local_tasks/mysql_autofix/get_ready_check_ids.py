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

from typing import Dict, List

from django.db.models import Q, QuerySet

from backend.db_meta.enums import MachineType
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.db_monitor.constants import MySQLAutofixStep
from backend.db_monitor.models import MySQLAutofixTicketStatus, MySQLAutofixTodo


def get_ready_check_ids(step: MySQLAutofixStep) -> List[int]:
    """
    多实例自愈合并及超时
    单机多实例 dbha 时会按实例产生 dbha 事件
    这些事件应该合并成一个自愈单据
    1. 每次调度时按 check_id 拿到故障 ip
    2. 检查 check_id-ip-port 事件数是否和 ip 的实例数一致
    3. 如果数量一致则开始自愈, 如果不一致则留给下一轮调度继续尝试
    4. 如果等待太久, 则自愈失败 ToDo: 如何定义 等待太久
    5. ToDo 这种等待太久的记录, 是否需要一个专门的自愈状态

    !!!! 不再考虑合并, 每个实例独立触发自愈 !!!!
    """
    query = Q(**{"current_step": step})
    if step == MySQLAutofixStep.IN_PLACE_AUTOFIX:
        query &= Q(**{"inplace_ticket_status": MySQLAutofixTicketStatus.UNSUBMITTED})
    else:
        query &= Q(**{"replace_ticket_status": MySQLAutofixTicketStatus.UNSUBMITTED})

    return list(MySQLAutofixTodo.objects.filter(query).values_list("check_id", flat=True))

    # res = []
    #
    # for row in (
    #     MySQLAutofixTodo.objects.filter(query)
    #     .values("check_id", "bk_cloud_id", "ip", "machine_type")
    #     .annotate(cnt=Count("check_id"))
    # ):
    #     cnt = row["cnt"]
    #     check_id = row["check_id"]
    #
    #     instances = _list_instances(row)
    #
    #     if cnt < instances.count():
    #         event_create_time_min = MySQLAutofixTodo.objects.filter(check_id=check_id,).aggregate(
    #             event_create_time=Min("event_create_time")
    #         )["event_create_time"]
    #         # 如果最早的事件已经是 15 min 之前, 则认为等太久了
    #         # 什么也不干, 等下一轮检查调度
    #         if event_create_time_min < datetime.datetime.now() - datetime.timedelta(minutes=15):
    #             # ToDo
    #             raise Exception("too long to wait")
    #     elif cnt > instances.count():
    #         raise Exception("impossible")
    #     else:
    #         res.append(check_id)
    #
    # return res


def _list_instances(r: Dict) -> QuerySet:  # List[Union[ProxyInstance, StorageInstance]]:
    ip = r["ip"]
    machine_type = r["machine_type"]
    bk_cloud_id = r["bk_cloud_id"]

    if machine_type in [MachineType.PROXY, MachineType.SPIDER]:
        return ProxyInstance.objects.filter(machine__bk_cloud_id=bk_cloud_id, machine__ip=ip)
    elif machine_type in [MachineType.SINGLE, MachineType.REMOTE]:
        return StorageInstance.objects.filter(machine__bk_cloud_id=bk_cloud_id, machine__ip=ip)
    else:
        raise Exception("invalid machine_type: {}".format(machine_type))
