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
from unittest.mock import patch

import pytest
from blueapps.account.models import User

from backend.ticket.constants import FlowType, TicketFlowStatus, TicketStatus, TicketType, TodoStatus, TodoType
from backend.ticket.exceptions import TodoWrongOperatorException
from backend.ticket.models import Flow, Ticket, Todo
from backend.ticket.todos import TodoActionType, TodoActorFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def mock_flow_signal():
    """断开 Flow 的 post_save 信号

    建 ITSM flow 会触发 TicketFlowManager.update_ticket_status -> ItsmFlow._status -> 真实调 ITSM 接口，
    在无外网/无法解析域名的环境(如 CI)会直接抛 ApiRequestError。
    """
    from django.db.models.signals import post_save

    from backend.ticket.models import Flow as FlowModel
    from backend.ticket.signals import update_ticket_status

    post_save.disconnect(update_ticket_status, sender=FlowModel)
    yield
    post_save.connect(update_ticket_status, sender=FlowModel)


def _prepare_itsm_todo(test_ticket_bk_biz_id, ticket_id=2201):
    """待审批单据 + ITSM 待办：审批人为 dba1(处理人)、dba2(协助人)"""
    ticket = Ticket.objects.create(
        id=ticket_id,
        bk_biz_id=test_ticket_bk_biz_id,
        ticket_type=TicketType.MYSQL_HA_APPLY,
        status=TicketStatus.APPROVE,
        creator="creator",
        updater="creator",
        remark="test itsm todo process",
        details={"nodes": {}},
        group=TicketType.MYSQL_HA_APPLY.value,
    )
    flow = Flow.objects.create(
        ticket=ticket,
        flow_type=FlowType.BK_ITSM,
        flow_alias="单据审批",
        details={
            "fields": [
                {"key": "approver", "value": "dba1,dba2"},
                {"key": "approval_result", "value": "true"},
            ]
        },
        status=TicketFlowStatus.RUNNING,
    )
    # ITSM 待办的 operators/helpers 由 flow.details 的 approver 推导：dba1 处理人、dba2 协助人
    todo = Todo.objects.create(
        ticket=ticket,
        flow=flow,
        name="单据等待审批",
        type=TodoType.ITSM,
        status=TodoStatus.TODO,
        context={"flow_id": flow.id, "ticket_id": ticket.id},
    )
    return ticket, flow, todo


@patch("backend.ticket.handler.TicketHandler.operate_itsm_ticket")
def test_superuser_refuse_itsm_todo_as_admin(mock_operate_itsm, test_ticket_bk_biz_id):
    """超管拒绝单据：调 ITSM 用 admin 身份(避免 ITSM 报接口异常)，DBM 侧仍记录真实操作人"""
    ticket, _, todo = _prepare_itsm_todo(test_ticket_bk_biz_id)
    User.objects.create(username="super_x", is_superuser=True)

    TodoActorFactory.actor(todo).process("super_x", TodoActionType.TERMINATE, {"remark": "TT", "version": 0})

    mock_operate_itsm.assert_called_once()
    call_kwargs = mock_operate_itsm.call_args.kwargs
    assert call_kwargs["operator"] == "admin"
    assert call_kwargs["is_approved"] is False

    # 审计信息保留真实操作人，不能被 admin 覆盖
    todo.refresh_from_db()
    ticket.refresh_from_db()
    assert todo.done_by == "super_x"
    assert ticket.updater == "super_x"


@patch("backend.ticket.handler.TicketHandler.operate_itsm_ticket")
def test_superuser_approve_itsm_todo_as_admin(mock_operate_itsm, test_ticket_bk_biz_id):
    """超管审批通过：调 ITSM 用 admin 身份，DBM 侧仍记录真实操作人"""
    _, _, todo = _prepare_itsm_todo(test_ticket_bk_biz_id)
    User.objects.create(username="super_x", is_superuser=True)

    TodoActorFactory.actor(todo).process("super_x", TodoActionType.APPROVE, {"remark": "ok", "version": 0})

    mock_operate_itsm.assert_called_once()
    call_kwargs = mock_operate_itsm.call_args.kwargs
    assert call_kwargs["operator"] == "admin"
    assert call_kwargs["is_approved"] is True

    todo.refresh_from_db()
    assert todo.done_by == "super_x"


@patch("backend.ticket.handler.TicketHandler.operate_itsm_ticket")
def test_creator_withdraw_itsm_todo_keeps_creator(mock_operate_itsm, test_ticket_bk_biz_id):
    """提单人撤单：必须用提单人本人身份调 ITSM，不能被 admin 兜底替换"""
    _, _, todo = _prepare_itsm_todo(test_ticket_bk_biz_id)

    TodoActorFactory.actor(todo).process("creator", TodoActionType.TERMINATE, {"remark": "TT"})

    call_kwargs = mock_operate_itsm.call_args.kwargs
    assert call_kwargs["operator"] == "creator"
    assert call_kwargs["action"] == "WITHDRAW"

    todo.refresh_from_db()
    assert todo.done_by == "creator"


@patch("backend.ticket.handler.TicketHandler.operate_itsm_ticket")
def test_approver_refuse_itsm_todo_keeps_self(mock_operate_itsm, test_ticket_bk_biz_id):
    """真实审批人拒绝单据：保持自己的身份调 ITSM"""
    _, _, todo = _prepare_itsm_todo(test_ticket_bk_biz_id)
    User.objects.create(username="dba1", is_superuser=False)

    TodoActorFactory.actor(todo).process("dba1", TodoActionType.TERMINATE, {"remark": "TT", "version": 0})

    mock_operate_itsm.assert_called_once()
    assert mock_operate_itsm.call_args.kwargs["operator"] == "dba1"
    todo.refresh_from_db()
    assert todo.done_by == "dba1"


@patch("backend.ticket.handler.TicketHandler.operate_itsm_ticket")
def test_normal_user_cannot_refuse_itsm_todo(mock_operate_itsm, test_ticket_bk_biz_id):
    """既非审批人也不是超管的用户，在待办层就被拦住，不会调到 ITSM"""
    _, _, todo = _prepare_itsm_todo(test_ticket_bk_biz_id)
    User.objects.create(username="normal_x", is_superuser=False)

    with pytest.raises(TodoWrongOperatorException):
        TodoActorFactory.actor(todo).process("normal_x", TodoActionType.TERMINATE, {"remark": "TT", "version": 0})

    mock_operate_itsm.assert_not_called()
