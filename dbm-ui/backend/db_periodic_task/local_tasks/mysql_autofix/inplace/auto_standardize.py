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
import datetime
import logging
from typing import Dict

from django.db.models import Min

from backend.db_meta.enums import InstanceInnerRole, InstanceStatus
from backend.db_meta.models import StorageInstance, StorageInstanceTuple
from backend.db_monitor.models import MySQLAutofixTicketStatus, MySQLAutofixTodo
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("celery")


def autofix_standardize(r: Dict):
    bk_cloud_id = r["bk_cloud_id"]
    bk_biz_id = r["bk_biz_id"]  # 这里其实是个隐式约束, 只能有一个业务id
    ip = r["ip"]
    check_id = r["check_id"]

    # 必须是不可用实例
    port_list = list(
        StorageInstance.objects.filter(
            machine__bk_cloud_id=bk_cloud_id,
            bk_biz_id=bk_biz_id,
            machine__ip=ip,
            status=InstanceStatus.UNAVAILABLE,
            instance_inner_role=InstanceInnerRole.SLAVE,
        ).values_list("port", flat=True)
    )

    logger.info("storage {}:{} {} dbha events found: {}".format(ip, port_list, r["port__count"], r))

    # 机器的所有端口 dbha 事件都上报了才会触发自愈
    # 否则会轮空
    if len(port_list) < r["port__count"]:
        min_create_at = (
            MySQLAutofixTodo.objects.filter(check_id=check_id)
            .values("create_at")
            .aggregate(Min("create_at"))["create_at__min"]
        )

        # 10 分钟机器的所有端口都没有上报完, 则认为有问题
        if datetime.datetime.now(datetime.timezone.utc) - min_create_at > datetime.timedelta(minutes=20):
            msg = "{} dbha event wait too long from {}".format(ip, min_create_at)
            logger.error(msg)

            # 放弃自愈
            MySQLAutofixTodo.objects.filter(check_id=check_id).update(
                inplace_ticket_status=MySQLAutofixTicketStatus.TIMEOUT
            )

            raise Exception(msg)  # ToDo
        return

    # ip 肯定是 slave
    # 给对端 ip 重新下发周边配置
    peer_ip = StorageInstanceTuple.objects.filter(receiver__machine__ip=ip).first().ejector.machine.ip

    tk = Ticket.create_ticket(
        ticket_type=TicketType.MYSQL_STORAGE_STANDARDIZE_AUTOFIX,
        creator="system",
        bk_biz_id=bk_biz_id,
        remark=TicketType.MYSQL_STORAGE_STANDARDIZE_AUTOFIX,
        details={
            "bk_cloud_id": bk_cloud_id,
            "bk_biz_id": bk_biz_id,
            "ip": peer_ip,
            "cluster_id": StorageInstance.objects.filter(machine__ip=ip).first().cluster.first().id,
        },
    )

    MySQLAutofixTodo.objects.filter(check_id=check_id).update(
        inplace_ticket_id=tk.id, inplace_ticket_status=MySQLAutofixTicketStatus.PENDING
    )
