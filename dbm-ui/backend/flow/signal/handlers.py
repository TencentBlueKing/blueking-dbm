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
import logging.config

from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext as _
from pipeline.eri.signals import post_set_state

from backend.db_dirty.handlers import DBDirtyMachineHandler
from backend.flow.consts import FAILED_STATES, StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.models import FlowNode, FlowTree
from backend.ticket.builders import BuilderFactory
from backend.ticket.constants import FlowCallbackType, FlowType, TicketFlowStatus
from backend.ticket.flow_manager.inner import InnerFlow
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.models import Flow, Ticket
from backend.utils.basic import get_target_items_from_details

logger = logging.getLogger("flow")


@receiver(post_set_state, dispatch_uid="_post_set_state_handler")
def post_set_state_signal_handler(sender, node_id, to_state, version, root_id, *args, **kwargs):
    engine = BambooEngine(root_id=root_id)
    pipeline_states = engine.get_pipeline_states().data

    now = timezone.now()
    logger.debug(_("【状态信号捕获】{} root_id={}, node_id={}, status:{}").format(now, root_id, node_id, to_state))
    if to_state == StateType.RUNNING:
        # 记录开始时间
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(started_at=now)

    FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(
        version_id=version, status=to_state, updated_at=now
    )
    try:
        tree = FlowTree.objects.get(root_id=root_id)
    except FlowTree.DoesNotExist:
        logger.debug(_("【状态信号捕获】未查找到FlowTree root_id={}").format(root_id))
        return

    # 流转当前的flow状态
    origin_tree_status = tree.status
    # 如果当前节点或者流程已失败，则状态为失败
    if to_state == StateType.FAILED or pipeline_states[root_id]["state"] == StateType.FAILED:
        target_tree_status = StateType.FAILED
    # 如果流程已撤销，则状态为撤销
    elif pipeline_states[root_id]["state"] == StateType.REVOKED:
        target_tree_status = StateType.REVOKED
    # 如果当前节点和流程都已完成，则状态为完成
    elif to_state == StateType.FINISHED and pipeline_states[root_id]["state"] == StateType.FINISHED:
        target_tree_status = StateType.FINISHED
    # 如果当前节点已完成，流程不处于完成态，则状态为进行
    elif to_state == StateType.FINISHED and pipeline_states[root_id]["state"] != StateType.FINISHED:
        target_tree_status = StateType.RUNNING
    else:
        target_tree_status = to_state

    # 如果状态发生改变，则触发单据回调和污点池转移
    if origin_tree_status != target_tree_status:
        try:
            # 更新flow tree和inner flow的状态
            tree.updated_at, tree.status = now, target_tree_status
            tree.save()
            handle_dirty_machine(tree.uid, root_id, origin_tree_status, target_tree_status)
            callback_ticket(tree.uid, root_id)
        except Exception as e:  # pylint: disable=broad-except
            logger.debug(_("【状态信号捕获】污点池处理/回调单据 发生错误，错误信息{}").format(e))
            return


def callback_ticket(ticket_id, root_id):
    """回调单据以进行后续的步骤"""
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except (Ticket.DoesNotExist, ValueError):
        return

    # 初始化结束后，流转为当前流程，执行inner后继动作，再进行回调
    current_flow = ticket.current_flow()

    # 在认为inner flow执行结束情况下，执行inner flow的后继动作
    inner_flow_obj = InnerFlow(flow_obj=current_flow)
    if inner_flow_obj.status not in [TicketFlowStatus.PENDING, TicketFlowStatus.RUNNING]:
        inner_flow_obj.callback(callback_type=FlowCallbackType.POST_CALLBACK.value)

    # 如果flow type的类型为快速任务，则跳过callback
    if current_flow.flow_type == FlowType.QUICK_INNER_FLOW:
        return

    if current_flow and current_flow.flow_obj_id == root_id:
        manager = TicketFlowManager(ticket=ticket)
        manager.run_next_flow()


def handle_dirty_machine(ticket_id, root_id, origin_tree_status, target_tree_status):
    """处理执行失败/重试成功涉及的污点池机器"""
    if (origin_tree_status not in FAILED_STATES) and (target_tree_status not in FAILED_STATES):
        return

    try:
        ticket = Ticket.objects.get(id=ticket_id)
        flow = Flow.objects.get(flow_obj_id=root_id)
        # 如果不是部署类单据，则无需处理
        if ticket.ticket_type not in BuilderFactory.apply_ticket_type:
            return
    except (Ticket.DoesNotExist, Flow.DoesNotExist, ValueError):
        return

    # 如果初始状态是失败，则证明是重试，将机器从污点池中移除
    bk_host_ids = get_target_items_from_details(
        obj=ticket.details, match_keys=["host_id", "bk_host_id", "bk_host_ids"]
    )
    if origin_tree_status in FAILED_STATES:
        logger.info(_("【状态信号捕获】主机列表:{} 将从污点池挪出").format(bk_host_ids))
        DBDirtyMachineHandler.remove_dirty_machines(bk_host_ids)

    # 如果是目标状态失败，则证明是执行失败，将机器加入污点池
    if target_tree_status in FAILED_STATES:
        logger.info(_("【状态信号捕获】单据-{}：任务-{}执行失败，主机列表:{}将挪到污点池").format(ticket_id, root_id, bk_host_ids))
        DBDirtyMachineHandler.insert_dirty_machines(
            bk_biz_id=ticket.bk_biz_id, bk_host_ids=bk_host_ids, ticket=ticket, flow=flow
        )
