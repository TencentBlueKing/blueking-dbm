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

from django.db import transaction

from backend.core import notify
from backend.ticket import constants
from backend.ticket.constants import FLOW_FINISHED_STATUS, FlowType, TicketStatus
from backend.ticket.flow_manager.delivery import DeliveryFlow, DescribeTaskFlow
from backend.ticket.flow_manager.inner import IgnoreResultInnerFlow, InnerFlow, QuickInnerFlow
from backend.ticket.flow_manager.itsm import ItsmFlow
from backend.ticket.flow_manager.pause import PauseFlow
from backend.ticket.flow_manager.resource import (
    ResourceApplyFlow,
    ResourceBatchApplyFlow,
    ResourceBatchDeliveryFlow,
    ResourceDeliveryFlow,
)
from backend.ticket.flow_manager.timer import TimerFlow
from backend.ticket.models import Ticket

SUPPORTED_FLOW_MAP = {
    FlowType.BK_ITSM.value: ItsmFlow,
    FlowType.INNER_FLOW.value: InnerFlow,
    FlowType.QUICK_INNER_FLOW.value: QuickInnerFlow,
    FlowType.PAUSE.value: PauseFlow,
    FlowType.DELIVERY.value: DeliveryFlow,
    FlowType.IGNORE_RESULT_INNER_FLOW.value: IgnoreResultInnerFlow,
    FlowType.DESCRIBE_TASK.value: DescribeTaskFlow,
    FlowType.TIMER.value: TimerFlow,
    FlowType.RESOURCE_APPLY: ResourceApplyFlow,
    FlowType.RESOURCE_DELIVERY: ResourceDeliveryFlow,
    FlowType.RESOURCE_BATCH_APPLY: ResourceBatchApplyFlow,
    FlowType.RESOURCE_BATCH_DELIVERY: ResourceBatchDeliveryFlow,
}

logger = logging.getLogger("root")


class TicketFlowManager(object):
    def __init__(self, ticket: Ticket):
        self.ticket = ticket
        self.current_flow_obj = ticket.current_flow()
        self.current_ticket_flow = self.get_ticket_flow_cls(flow_type=self.current_flow_obj.flow_type)(
            ticket.current_flow()
        )

    @staticmethod
    def get_ticket_flow_cls(flow_type):
        try:
            return SUPPORTED_FLOW_MAP[flow_type]
        except KeyError:
            raise NotImplementedError(f"unsupported step type: {flow_type}")

    def run_next_flow(self):
        next_flow = self.ticket.next_flow()
        if not next_flow:
            # 没有下一个节点，说明流程已结束
            return

        # 满足下面两种条件之一，则继续执行下一个流程
        # 1. 初始状态的任务流程
        # 2. 当前流程已完成
        is_init_flow = next_flow.id == self.current_flow_obj.id
        if is_init_flow or self.current_ticket_flow.status in FLOW_FINISHED_STATUS:
            self.get_ticket_flow_cls(flow_type=next_flow.flow_type)(next_flow).run()

    def update_ticket_status(self):
        # 获取流程状态集合
        flow_status_map = {
            self.get_ticket_flow_cls(flow_type=flow.flow_type)(flow).status: flow for flow in self.ticket.flows.all()
        }
        statuses = set(flow_status_map.keys())
        logger.info(f"update_ticket_status for ticket:{self.ticket.id}, statuses: {statuses}")
        # 只要存在其中一个终止，则单据状态为已终止
        if constants.TicketFlowStatus.TERMINATED in statuses:
            target_status = constants.TicketStatus.TERMINATED
        # 只要存在其中一个失败，则单据状态为失败态
        elif constants.TicketFlowStatus.FAILED in statuses:
            target_status = constants.TicketStatus.FAILED
        # 只要存在其中一个撤销，则单据状态为撤销态
        elif constants.TicketFlowStatus.REVOKED in statuses:
            target_status = constants.TicketStatus.REVOKED
        # 只要有一个存在running，则需要根据flow的type决定单据的状态
        elif constants.TicketFlowStatus.RUNNING in statuses:
            flow = flow_status_map[constants.TicketFlowStatus.RUNNING]
            target_status = constants.RUNNING_FLOW__TICKET_STATUS.get(flow.flow_type, constants.TicketStatus.RUNNING)
        # 如果所有flow的状态处于完成态，则单据为成功
        elif statuses.issubset(set(FLOW_FINISHED_STATUS)):
            target_status = constants.TicketStatus.SUCCEEDED
        else:
            # 其他场景下状态未变更，无需更新DB
            return

        # 原子更新单据状态
        with transaction.atomic():
            ticket = Ticket.objects.select_for_update().get(id=self.ticket.id)
            if ticket.status == target_status:
                return
            origin_status, ticket.status = ticket.status, target_status
            ticket.save(update_fields=["status", "update_at"])
            self.ticket_status_trigger(origin_status, target_status)

    def ticket_status_trigger(self, origin_status, target_status):
        """单据状态更新后的钩子函数"""

        # 单据状态变更后，发送通知。
        # 忽略运行中：流转到内置任务无需通知，待继续在todo创建时才触发通知
        # 忽略待补货：到资源申请节点，单据状态总会流转为待补货，但是只有待补货todo创建才触发通知
        if target_status not in [TicketStatus.RUNNING, TicketStatus.RESOURCE_REPLENISH]:
            notify.send_msg.apply_async(args=(self.ticket.id,))
