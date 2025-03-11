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
from backend.db_monitor.constants import MySQLAutofixStep
from backend.db_monitor.models import MySQLAutofixTicketStatus, MySQLAutofixTodo
from backend.ticket.models import Ticket


def update_inplace_status():
    """
    检查并更新 pending, running 状态的原地自愈单据
    """
    records = MySQLAutofixTodo.objects.filter(
        current_step=MySQLAutofixStep.IN_PLACE_AUTOFIX,
        inplace_ticket_status__in=[MySQLAutofixTicketStatus.PENDING, MySQLAutofixTicketStatus.RUNNING],
    )
    for record in records:
        tk = Ticket.objects.get(pk=record.inplace_ticket_id)
        record.inplace_ticket_status = tk.status
        record.save(update_fields=["inplace_ticket_status"])


def trans_to_replace():
    records = MySQLAutofixTodo.objects.filter(
        current_step=MySQLAutofixStep.IN_PLACE_AUTOFIX, inplace_ticket_status=MySQLAutofixTicketStatus.FAILED
    )
    records.update(current_step=MySQLAutofixStep.REPLACE_NEW)
