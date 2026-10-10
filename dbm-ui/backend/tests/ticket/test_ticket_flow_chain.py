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
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.configuration.constants import DBType
from backend.tests.mock_data import constant
from backend.ticket.constants import FlowContext, FlowType, TicketFlowStatus, TicketStatus, TicketType
from backend.ticket.models import Flow, Ticket
from backend.ticket.models.ticket import sort_flows_by_next_flow

pytestmark = pytest.mark.django_db
logger = logging.getLogger("test")


def make_flow(flow_id, next_flow=None):
    """构造一个仅含 id/context 的轻量 flow，用于纯函数 sort_flows_by_next_flow 的单元测试。

    当 next_flow 为 None 时不写入 next_flow 键(模拟存量数据)；否则显式写入。
    """
    context = {}
    if next_flow is not None:
        context[FlowContext.NEXT_FLOW.value] = next_flow
    return SimpleNamespace(id=flow_id, context=context)


def make_flow_with_context(flow_id, context):
    """构造指定 context 的轻量 flow，便于构造 next_flow 显式为 None 的场景。"""
    return SimpleNamespace(id=flow_id, context=context)


# ==================== TestSortFlowsByNextFlow ====================


class TestSortFlowsByNextFlow:
    """测试 sort_flows_by_next_flow 纯函数：按 context.next_flow 指针排序，断链时兜底。"""

    def test_empty_flows_returns_empty_list(self):
        """空列表返回空列表"""
        assert sort_flows_by_next_flow([]) == []

    def test_single_flow_returns_itself(self):
        """单个 flow 直接返回"""
        flow = make_flow(1)
        assert [f.id for f in sort_flows_by_next_flow([flow])] == [1]

    def test_legacy_flows_without_next_flow_sorted_by_id(self):
        """存量数据未写入 next_flow，退化为按 id 升序排序"""
        flows = [make_flow(3), make_flow(1), make_flow(2)]
        assert [f.id for f in sort_flows_by_next_flow(flows)] == [1, 2, 3]

    def test_next_flow_none_values_treated_as_legacy(self):
        """next_flow 显式为 None 时视为无指针，仍按 id 升序排序"""
        next_key = FlowContext.NEXT_FLOW.value
        flows = [
            make_flow_with_context(2, {next_key: None}),
            make_flow_with_context(1, {next_key: None}),
        ]
        assert [f.id for f in sort_flows_by_next_flow(flows)] == [1, 2]

    def test_complete_chain_reorders_by_next_flow(self):
        """完整单链按 next_flow 指针排序，忽略输入顺序"""
        # 链: 1 -> 2 -> 3，输入顺序打乱为 3, 1, 2
        flows = [make_flow(3), make_flow(1, 2), make_flow(2, 3)]
        assert [f.id for f in sort_flows_by_next_flow(flows)] == [1, 2, 3]

    def test_chain_head_detected_regardless_of_input_order(self):
        """头节点(未被任何节点指向)始终排在最前"""
        # 链: 1 -> 2 -> 3，头节点 1 在输入中排在最后
        flows = [make_flow(2, 3), make_flow(3), make_flow(1, 2)]
        assert [f.id for f in sort_flows_by_next_flow(flows)] == [1, 2, 3]

    def test_broken_chain_unreachable_appended_by_id(self):
        """断链时，无法从头部到达的节点按 id 升序补在尾部"""
        # 链1: 1 -> 2 -> 3；链2: 4 -> 5(孤立)，二者互不相连
        flows = [make_flow(1, 2), make_flow(2, 3), make_flow(3), make_flow(4, 5), make_flow(5)]
        assert [f.id for f in sort_flows_by_next_flow(flows)] == [1, 2, 3, 4, 5]

    def test_multiple_heads_falls_back_to_first_head(self):
        """多链(多头)时从第一个头开始遍历，其余按 id 补在尾部"""
        # 两条互不相连的链: 1 -> 2 与 3(孤立)
        flows = [make_flow(1, 2), make_flow(2), make_flow(3)]
        assert [f.id for f in sort_flows_by_next_flow(flows)] == [1, 2, 3]

    def test_circular_chain_does_not_loop_forever(self):
        """环形链通过 visited 集合终止遍历，不会死循环"""
        # 环: 1 -> 2 -> 3 -> 1
        flows = [make_flow(1, 2), make_flow(2, 3), make_flow(3, 1)]
        result = [f.id for f in sort_flows_by_next_flow(flows)]
        assert sorted(result) == [1, 2, 3]
        assert len(result) == 3

    def test_next_flow_pointing_to_missing_id(self):
        """next_flow 指向不存在的 id 时，链在该处终止"""
        # 链: 1 -> 2 -> (99 不存在)
        flows = [make_flow(1, 2), make_flow(2, 99)]
        assert [f.id for f in sort_flows_by_next_flow(flows)] == [1, 2]


# ==================== Fixtures ====================


@pytest.fixture
def flow_chain_ticket(db):
    """构造一张单据，其 flow 通过 next_flow 指针形成单链，且链序与创建(id)序不同。

    模拟改单在中间插入节点的场景：确认修改节点 confirm 后建(id 最大)但位于链中，
    而尾巴 tail 先建(id 较小)却位于链尾。
    链序: itsm(SKIPPED) -> confirm(PENDING) -> tail(PENDING)
    id 序: itsm -> tail -> confirm
    """
    ticket = Ticket.objects.create(
        bk_biz_id=constant.BK_BIZ_ID,
        ticket_type=TicketType.MYSQL_SINGLE_APPLY,
        status=TicketStatus.RUNNING,
        creator="admin",
        updater="admin",
        remark="flow chain 测试单据",
        details={},
        group=DBType.MySQL.value,
    )
    # 创建顺序即 id 序：itsm < tail < confirm
    itsm = Flow.objects.create(ticket=ticket, flow_type=FlowType.BK_ITSM, status=TicketFlowStatus.SKIPPED, details={})
    tail = Flow.objects.create(
        ticket=ticket, flow_type=FlowType.INNER_FLOW, status=TicketFlowStatus.PENDING, details={}
    )
    confirm = Flow.objects.create(
        ticket=ticket, flow_type=FlowType.CONFIRM_MODIFY, status=TicketFlowStatus.PENDING, details={}
    )

    next_key = FlowContext.NEXT_FLOW.value
    itsm.context = {next_key: confirm.id}
    confirm.context = {next_key: tail.id}
    tail.context = {}
    for flow in (itsm, confirm, tail):
        flow.save(update_fields=["context", "update_at"])

    yield ticket, {"itsm": itsm, "tail": tail, "confirm": confirm}

    for flow in (itsm, confirm, tail):
        flow.delete()
    ticket.delete()


# ==================== TestTicketFlowChain ====================


class TestTicketFlowChain:
    """测试 Ticket.ordered_flows / current_flow / next_flow 对 next_flow 链序的感知。"""

    def test_ordered_flows_follows_next_flow_chain(self, flow_chain_ticket):
        """ordered_flows 按 next_flow 链排序，而非按 id 排序"""
        ticket, flows = flow_chain_ticket
        ordered = ticket.ordered_flows()
        assert [f.id for f in ordered] == [flows["itsm"].id, flows["confirm"].id, flows["tail"].id]

    def test_next_flow_returns_first_pending_in_chain_order(self, flow_chain_ticket):
        """next_flow 返回链上第一个 PENDING 节点(confirm)，而非 id 更小的尾巴 tail"""
        ticket, flows = flow_chain_ticket
        assert ticket.next_flow().id == flows["confirm"].id

    def test_current_flow_returns_last_non_pending_in_chain_order(self, flow_chain_ticket):
        """current_flow 返回链上最后一个非 PENDING 节点(itsm)"""
        ticket, flows = flow_chain_ticket
        assert ticket.current_flow().id == flows["itsm"].id

    def test_current_flow_prefers_chain_order_over_id_order(self, db):
        """链序与 id 序不同时，current_flow 以链序为准。

        创建(id)序: running -> pending -> skipped
        next_flow 链: skipped -> running -> pending
        按 id 排序时最后一个非 PENDING 是 skipped；按链排序则是 running。
        """
        ticket = Ticket.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY,
            status=TicketStatus.RUNNING,
            creator="admin",
            updater="admin",
            remark="current_flow 链序测试单据",
            details={},
            group=DBType.MySQL.value,
        )
        running = Flow.objects.create(
            ticket=ticket, flow_type=FlowType.INNER_FLOW, status=TicketFlowStatus.RUNNING, details={}
        )
        pending = Flow.objects.create(
            ticket=ticket, flow_type=FlowType.INNER_FLOW, status=TicketFlowStatus.PENDING, details={}
        )
        skipped = Flow.objects.create(
            ticket=ticket, flow_type=FlowType.BK_ITSM, status=TicketFlowStatus.SKIPPED, details={}
        )

        next_key = FlowContext.NEXT_FLOW.value
        skipped.context = {next_key: running.id}
        running.context = {next_key: pending.id}
        pending.context = {}
        for flow in (skipped, running, pending):
            flow.save(update_fields=["context", "update_at"])

        assert ticket.current_flow().id == running.id

        for flow in (skipped, running, pending):
            flow.delete()
        ticket.delete()

    def test_current_flow_all_pending_returns_next_flow(self, db):
        """所有 flow 均为 PENDING 时，current_flow 退化为 next_flow"""
        ticket = Ticket.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY,
            status=TicketStatus.PENDING,
            creator="admin",
            updater="admin",
            remark="全 pending 单据",
            details={},
            group=DBType.MySQL.value,
        )
        first = Flow.objects.create(
            ticket=ticket, flow_type=FlowType.INNER_FLOW, status=TicketFlowStatus.PENDING, details={}
        )
        second = Flow.objects.create(
            ticket=ticket, flow_type=FlowType.INNER_FLOW, status=TicketFlowStatus.PENDING, details={}
        )

        assert ticket.current_flow().id == first.id
        assert ticket.next_flow().id == first.id

        first.delete()
        second.delete()
        ticket.delete()

    def test_current_flow_empty_returns_none(self, db):
        """无任何 flow 时 current_flow 返回 None"""
        ticket = Ticket.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY,
            status=TicketStatus.PENDING,
            creator="admin",
            updater="admin",
            remark="空流程单据",
            details={},
            group=DBType.MySQL.value,
        )
        assert ticket.current_flow() is None
        assert ticket.next_flow() is None
        ticket.delete()

    def test_next_flow_all_finished_returns_none(self, db):
        """所有 flow 均已结束时 next_flow 返回 None"""
        ticket = Ticket.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY,
            status=TicketStatus.SUCCEEDED,
            creator="admin",
            updater="admin",
            remark="已结束单据",
            details={},
            group=DBType.MySQL.value,
        )
        done = Flow.objects.create(
            ticket=ticket, flow_type=FlowType.INNER_FLOW, status=TicketFlowStatus.SUCCEEDED, details={}
        )
        assert ticket.next_flow() is None
        done.delete()
        ticket.delete()

    def test_next_flow_itsm_skip_skips_itsm_and_pause(self, db):
        """ITSM_FLOW_SKIP 启用时跳过 BK_ITSM 与 PAUSE 节点"""
        ticket = Ticket.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY,
            status=TicketStatus.RUNNING,
            creator="admin",
            updater="admin",
            remark="ITSM skip 单据",
            details={},
            group=DBType.MySQL.value,
        )
        itsm = Flow.objects.create(
            ticket=ticket, flow_type=FlowType.BK_ITSM, status=TicketFlowStatus.PENDING, details={}
        )
        pause = Flow.objects.create(
            ticket=ticket, flow_type=FlowType.PAUSE, status=TicketFlowStatus.PENDING, details={}
        )
        inner = Flow.objects.create(
            ticket=ticket, flow_type=FlowType.INNER_FLOW, status=TicketFlowStatus.PENDING, details={}
        )

        with patch("backend.ticket.models.ticket.env") as mock_env:
            mock_env.ITSM_FLOW_SKIP = True
            assert ticket.next_flow().id == inner.id

        itsm.delete()
        pause.delete()
        inner.delete()
        ticket.delete()

    def test_next_flow_itsm_skip_no_remaining_returns_none(self, db):
        """ITSM_FLOW_SKIP 启用且只剩审批/暂停节点时 next_flow 返回 None"""
        ticket = Ticket.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            ticket_type=TicketType.MYSQL_SINGLE_APPLY,
            status=TicketStatus.RUNNING,
            creator="admin",
            updater="admin",
            remark="仅审批节点单据",
            details={},
            group=DBType.MySQL.value,
        )
        itsm = Flow.objects.create(
            ticket=ticket, flow_type=FlowType.BK_ITSM, status=TicketFlowStatus.PENDING, details={}
        )

        with patch("backend.ticket.models.ticket.env") as mock_env:
            mock_env.ITSM_FLOW_SKIP = True
            assert ticket.next_flow() is None

        itsm.delete()
        ticket.delete()
