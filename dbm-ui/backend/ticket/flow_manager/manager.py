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
from django.utils.translation import gettext as _

from backend.core import notify
from backend.iam_app.handlers.drf_perm.ticket import add_ticket_audit_event, audit_ticket_status
from backend.ticket import constants
from backend.ticket.builders import BuilderFactory
from backend.ticket.constants import FLOW_FINISHED_STATUS, FlowType, TicketStatus, TicketType
from backend.ticket.flow_manager.delivery import DeliveryFlow, DescribeTaskFlow
from backend.ticket.flow_manager.inner import (
    HCMReplenishResourceTaskFlow,
    IgnoreResultInnerFlow,
    InnerFlow,
    QuickInnerFlow,
    SimpleTaskFlow,
)
from backend.ticket.flow_manager.itsm import ItsmFlow
from backend.ticket.flow_manager.pause import PauseFlow
from backend.ticket.flow_manager.resource import ResourceApplyFlow, ResourceBatchApplyFlow, ResourceDeliveryFlow
from backend.ticket.flow_manager.timer import TimerFlow
from backend.ticket.models import Ticket
from backend.ticket.tasks.ticket_tasks import create_cluster_todo, create_recycle_ticket

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
    FlowType.RESOURCE_BATCH_DELIVERY: ResourceDeliveryFlow,
    FlowType.RESOURCE_BATCH_APPLY: ResourceBatchApplyFlow,
    FlowType.HOST_RECYCLE: SimpleTaskFlow,
    FlowType.RESOURCE_HCM_REPLENISH: HCMReplenishResourceTaskFlow,
}

logger = logging.getLogger("root")


class TicketFlowManager(object):
    def __init__(self, ticket: Ticket):
        self.ticket = ticket

    @staticmethod
    def get_ticket_flow_cls(flow_type):
        try:
            return SUPPORTED_FLOW_MAP[flow_type]
        except KeyError:
            raise NotImplementedError(f"unsupported step type: {flow_type}")

    def run_next_flow(self):
        next_flow = self.ticket.next_flow()
        current_flow = self.ticket.current_flow()

        # 没有下一个节点，说明流程已结束
        if not next_flow:
            logger.error(_("无可执行的下一流程"))
            return

        # 先取下一个流程，再取当前流程，可以根据流程的顺序保证并发的一致性
        # 如果current_flow晚于next_flow，说明流程已经发起
        is_init_flow = next_flow.id == self.ticket.flows.first().id

        if current_flow.id >= next_flow.id and not is_init_flow:
            logger.error(_("流程非预期：当前流程晚于下一个流程"))
            return

        # 满足下面两种条件之一，则继续执行下一个流程
        # 1. 初始状态的任务流程
        # 2. 当前流程已完成
        current_flow_status = self.get_ticket_flow_cls(flow_type=current_flow.flow_type)(current_flow).status
        if is_init_flow or current_flow_status in FLOW_FINISHED_STATUS:
            logger.info(_("[{}]流程已触发:{}").format(self.ticket.id, next_flow.flow_alias))
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
            origin_status, ticket.status = ticket.status, target_status
            if origin_status == target_status:
                return
            ticket.save(update_fields=["status", "update_at"])

        # 执行状态更新钩子函数
        self.ticket_status_trigger(origin_status, target_status)

    def ticket_status_trigger(self, origin_status, target_status):
        """单据状态更新后的钩子函数。注：如果钩子函数非关键链路，请异步发起"""

        # 上报单据状态流转事件，针对任务运行、成功、失败、终止状态上报
        if target_status in audit_ticket_status:
            add_ticket_audit_event.apply_async(args=(self.ticket.id,))

        # 单据状态变更后，发送通知。
        # 忽略运行中：流转到内置任务无需通知，待继续在todo创建时才触发通知
        # 忽略待补货：到资源申请节点，单据状态总会流转为待补货，但是只有待补货todo创建才触发通知
        # 忽略审批：创建itsm单据后，发送通知
        if target_status not in [TicketStatus.RUNNING, TicketStatus.RESOURCE_REPLENISH, TicketStatus.APPROVE]:
            notify.send_msg.apply_async(args=(self.ticket.id,))

        # 如果是待下架单据，正常结束要联动回收主机
        is_recycle = self.ticket.ticket_type in BuilderFactory.recycle_ticket_type
        if target_status == TicketStatus.SUCCEEDED and is_recycle:
            recycle_hosts = self.ticket.details.get("recycle_hosts", [])
            create_recycle_ticket.apply_async(args=(self.ticket.id, recycle_hosts, TicketType.RECYCLE_OLD_HOST))

        # 如果是部署类单据，异常终止要联动回收主机
        is_apply = self.ticket.ticket_type in BuilderFactory.apply_ticket_type
        if target_status == TicketStatus.TERMINATED and is_apply:
            create_recycle_ticket.apply_async(args=(self.ticket.id, [], TicketType.RECYCLE_APPLY_HOST))

        # 如果是集群的禁用、启动、删除、sqlserver重置则处理相对应代办操作
        if (
            self.ticket.ticket_type in BuilderFactory.ticket_type__cluster_phase
            and target_status == TicketStatus.SUCCEEDED
        ):
            create_cluster_todo.apply_async(
                args=(self.ticket.id, BuilderFactory.ticket_type__cluster_phase[self.ticket.ticket_type])
            )
