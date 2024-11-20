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
from backend.ticket.constants import FlowType, TicketFlowStatus
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.models import Flow, Ticket


def update_ticket_status(sender, instance: Flow, **kwargs):
    """
    更新 ticket flow 状态的同时，更新单据状态，保证一致性
    """
    if not instance.pk:
        return

    # 如果是inner flow的终止，要联动回收主机
    if instance.flow_type == FlowType.INNER_FLOW and instance.status == TicketFlowStatus.TERMINATED:
        Ticket.create_recycle_ticket(revoke_ticket_id=instance.ticket.id)

    TicketFlowManager(instance.ticket).update_ticket_status()
