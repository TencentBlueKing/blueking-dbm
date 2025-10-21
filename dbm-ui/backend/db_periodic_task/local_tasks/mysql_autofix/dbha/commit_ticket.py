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
import threading
from typing import List

from backend.db_monitor.models import MySQLDBHAAutofixTicketStageQueue
from backend.ticket.constants import TicketFlowStatus
from backend.ticket.models import Ticket

mysql_dbha_af_commiter_lock = threading.Lock()


# @transaction.atomic
def commit_ticket(uncommit_tickets: List[MySQLDBHAAutofixTicketStageQueue]):
    """
    这里拿到的输入, queue_uuid 可能会有重复的
    每一个 queue_uuid 只要随便拿一行来提单就行
    """
    with mysql_dbha_af_commiter_lock:
        commited = []
        for ut in uncommit_tickets:
            if ut.queue_uuid in commited:
                continue

            ticket_param = ut.ticket_param
            tk = Ticket.create_ticket(**ticket_param)
            MySQLDBHAAutofixTicketStageQueue.objects.filter(queue_uuid=ut.queue_uuid).update(
                ticket_id=tk.pk, status=TicketFlowStatus.PENDING
            )
            commited.append(ut.queue_uuid)
