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
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from django.db.models import Count, Min
from django_mysql.models import GroupConcat

from backend.db_meta.enums import MachineType
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.db_monitor.models import MySQLAutofixTicketStatus, MySQLAutofixTodo
from backend.db_periodic_task.local_tasks.mysql_autofix.exception import (
    MySQLDBHAAutofixBadTodoRecord,
    MySQLDBHAAutofixMissingRecord,
    MySQLDBHAAutofixWaitTimeout,
)


class GroupedTodo(object):
    def __init__(
        self,
        check_id: int,
        bk_cloud_id: int,
        bk_biz_id: int,
        ip: str,
        cnt: int,
        cluster_ids: List[int],
        machine_type: MachineType,
        ticket_id: int,
        status: MySQLAutofixTicketStatus,
    ):
        self.check_id = check_id
        self.bk_cloud_id = bk_cloud_id
        self.bk_biz_id = bk_biz_id
        self.ip = ip
        self.cnt = cnt
        self.cluster_ids = cluster_ids
        self.machine_type = machine_type
        self.ticket_id = ticket_id
        self.status = status


def group_todo() -> List[GroupedTodo]:
    res = []
    for row in (
        MySQLAutofixTodo.objects.filter(
            status__in=[
                MySQLAutofixTicketStatus.UNSUBMITTED,
                MySQLAutofixTicketStatus.PENDING,
                MySQLAutofixTicketStatus.RUNNING,
            ]
        )
        .values("check_id", "bk_cloud_id", "bk_biz_id", "ip")
        .annotate(
            cnt=Count("check_id"),
            cluster_ids=GroupConcat("cluster_id"),
            machine_types=GroupConcat("machine_type"),
            ticket_ids=GroupConcat("ticket_id"),
            statuses=GroupConcat("status"),
        )
    ):
        cluster_ids = [int(cluster_id) for cluster_id in list(set(row["cluster_ids"].split(",")))]
        try:
            machine_type, ticket_id, status = validate_group(row)
        except MySQLDBHAAutofixMissingRecord:
            # 专门用来再等一轮的异常
            # 说明同机器所有实例的 dbha 事件还没全上报
            continue
        except (MySQLDBHAAutofixWaitTimeout, MySQLDBHAAutofixBadTodoRecord):
            # ToDo warning call
            continue

        res.append(
            GroupedTodo(
                check_id=row["check_id"],
                bk_cloud_id=row["bk_cloud_id"],
                bk_biz_id=row["bk_biz_id"],
                ip=row["ip"],
                cnt=row["cnt"],
                cluster_ids=cluster_ids,
                machine_type=machine_type,
                ticket_id=ticket_id,
                status=status,
            )
        )

    return res


def validate_group(row: Dict) -> (str, int, str):
    mts = list(set([mt.strip(" ") for mt in row["machine_types"].split(",")]))
    ticket_ids = [int(ticket_id) for ticket_id in list(set(row["ticket_ids"].split(",")))]
    sts = list(set([st.strip(" ") for st in row["statuses"].split(",")]))

    if len(mts) > 1 or len(ticket_ids) > 1 or len(sts) > 1:
        MySQLAutofixTodo.objects.filter(check_id=row["check_id"]).update(status=MySQLAutofixTicketStatus.TERMINATED)
        raise MySQLDBHAAutofixBadTodoRecord(check_id=row["check_id"])

    if sts[0] == MySQLAutofixTicketStatus.UNSUBMITTED and ticket_ids[0] != 0:
        raise MySQLDBHAAutofixBadTodoRecord(check_id=row["check_id"])

    if sts[0] in [MySQLAutofixTicketStatus.PENDING, MySQLAutofixTicketStatus.RUNNING] and ticket_ids[0] == 0:
        raise MySQLDBHAAutofixBadTodoRecord(check_id=row["check_id"])

    if mts[0] in [MachineType.PROXY, MachineType.SPIDER]:
        instance_count = ProxyInstance.objects.filter(machine__bk_cloud_id=row["bk_cloud_id"], machine__ip=row["ip"])
    else:
        instance_count = StorageInstance.objects.filter(machine__bk_cloud_id=row["bk_cloud_id"], machine__ip=row["ip"])

    if row["cnt"] < instance_count.count():
        event_create_time_min = MySQLAutofixTodo.objects.filter(check_id=row["check_id"]).aggregate(
            event_create_time=Min("event_create_time")
        )["event_create_time"]

        # 等太久了, 超时放弃
        if event_create_time_min > datetime.now(timezone.utc) - timedelta(minutes=15):
            MySQLAutofixTodo.objects.filter(check_id=row["check_id"]).update(status=MySQLAutofixTicketStatus.TIMEOUT)
            raise MySQLDBHAAutofixWaitTimeout(check_id=row["check_id"])
        else:  # 再等等
            raise MySQLDBHAAutofixMissingRecord
    elif row["cnt"] > instance_count.count():
        raise MySQLDBHAAutofixBadTodoRecord(check_id=row["check_id"])

    return mts[0], ticket_ids[0], sts[0]
