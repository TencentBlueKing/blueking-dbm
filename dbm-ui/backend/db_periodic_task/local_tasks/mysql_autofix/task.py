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
import logging

from celery.schedules import crontab
from django.db import transaction
from django.db.models import Q

from backend.db_meta.enums import InstanceStatus, MachineType
from backend.db_meta.models import Cluster
from backend.db_monitor.models import MySQLAutofixTicketStatus, MySQLAutofixTodo
from backend.db_periodic_task.local_tasks.mysql_autofix import inplace
from backend.db_periodic_task.local_tasks.mysql_autofix.status_trans import trans_records_status
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.ticket.constants import TicketStatus
from backend.ticket.models import Ticket

logger = logging.getLogger("celery")


@transaction.atomic
@register_periodic_task(run_every=crontab(minute="*"))
def mysql_autofix():
    """
    有自愈单据处理时, doing = True
    如果这个单据异常退出了, doing 保持 True, 无法被再次消费
    这时候需要检查自愈相关单据, 如果没有单据处理, 需要修复 doing
    自愈相关的单据

    启动 proxy:
    MYSQL_AUTOFIX_PROXY_INPLACE_AUTOFIX



    自愈完成后, finish = True
    如果这个单据异常退出了, finish 保持 False, 会被重复自愈
    这个时候去检查对应集群元数据, 如果是正常的说明自愈其实完成了, 可以避免重复自愈
    """
    logger.info("start mysql dbha autofix dispatch")

    trans_records_status()

    inplace.autofix()
    # inplace.autofix(get_ready_check_ids(MySQLAutofixStep.IN_PLACE_AUTOFIX))
    # replace.autofix(get_ready_check_ids(MySQLAutofixStep.REPLACE_NEW))
    # implicit_fixed()


def implicit_fixed():
    """
    自愈未开始时, 如果集群元数据已经正常, 则终止自愈
    1. pending 状态的可以终止, 这时候已经提单了
    2. 状态为 unsubmitted 的还没提单, 也可以终止
    """
    logger.info("start implicit autofix")
    records = MySQLAutofixTodo.objects.filter(
        Q(inplace_ticket_status=TicketStatus.PENDING.value)
        | Q(replace_ticket_status=TicketStatus.PENDING.value)
        | Q(inplace_ticket_status=MySQLAutofixTicketStatus.UNSUBMITTED.value)
        | Q(replace_ticket_status=MySQLAutofixTicketStatus.UNSUBMITTED.value)
    )
    for record in records:
        cluster_obj = Cluster.objects.get(id=record.cluster_id, cluster_type=record.cluster_type)
        if (
            record.machine_type in [MachineType.PROXY, MachineType.SPIDER]
            and not cluster_obj.proxyinstance_set.filter(
                machine__ip=record.ip, port=record.port, status=InstanceStatus.UNAVAILABLE.value
            ).exists()
        ) or (
            record.machine_type in [MachineType.BACKEND, MachineType.REMOTE, MachineType.SINGLE]
            and not cluster_obj.storageinstance_set.filter(
                machine__ip=record.ip, port=record.port, status=InstanceStatus.UNAVAILABLE.value
            ).exists()
        ):
            logger.info("{} already recovered, skip autofix".format(record))
            record.inplace_ticket_status = MySQLAutofixTicketStatus.SKIPPED.value
            record.replace_ticket_status = MySQLAutofixTicketStatus.SKIPPED.value

            if record.inplace_ticket_id > 0:
                logger.info("terminate inplace ticket: {}".format(record.inplace_ticket_id))
                record.inplace_ticket_status = MySQLAutofixTicketStatus.TERMINATED.value
                tk = Ticket.objects.get(pk=record.inplace_ticket_id)
                tk.set_terminated()
                # ToDo 真实的终止单据流程

            if record.replace_ticket_id > 0:
                logger.info("terminate replace ticket: {}".format(record.replace_ticket_id))
                record.replace_ticket_status = MySQLAutofixTicketStatus.TERMINATED.value
                tk = Ticket.objects.get(pk=record.replace_ticket_id)
                tk.set_terminated()
                # ToDo 真实的终止单据流程

            record.save(update_fields=["inplace_ticket_status", "replace_ticket_status"])

    logger.info("finish implicit autofix")
