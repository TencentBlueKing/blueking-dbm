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
from dataclasses import dataclass

from backend.constants import DEFAULT_SYSTEM_USER
from backend.ticket import todos
from backend.ticket.constants import TODO_RUNNING_STATUS, OperateNodeActionType, TodoType
from backend.ticket.todos import ActionType, BaseTodoContext

logger = logging.getLogger("root")


@dataclass
class ItsmTodoContext(BaseTodoContext):
    pass


@todos.TodoActorFactory.register(TodoType.ITSM)
class ItsmTodo(todos.TodoActor):
    """来自审批中的待办"""

    def process(self, username, action, params):
        # itsm的todo允许本人操作
        if username == self.todo.ticket.creator and self.todo.status in TODO_RUNNING_STATUS:
            self._process(username, action, params)
            return
        super().process(username, action, params)

    def _process(self, username, action, params):
        from backend.ticket.handler import TicketHandler

        ticket_id = self.context.get("ticket_id")
        own = self.todo.ticket.creator
        message = params.get("remark", "")

        def approve_itsm_ticket(itsm_action, is_approved):
            sn = TicketHandler.approve_itsm_ticket(
                ticket_id,
                action=itsm_action,
                operator=username,
                is_approved=is_approved,
                action_message=message,
            )
            return sn

        # 系统终止，认为是关单(调用itsm接口要用admin发起)
        if action == ActionType.TERMINATE and username == DEFAULT_SYSTEM_USER:
            username = "admin"
            approve_itsm_ticket(OperateNodeActionType.TERMINATE, is_approved=False)
            self.todo.set_terminated(username, action)
        # 审批人终止，认为是拒单
        elif action == ActionType.TERMINATE and username != own:
            approve_itsm_ticket(OperateNodeActionType.TRANSITION, is_approved=False)
            self.todo.set_terminated(username, action)
        # 自己终止，认为是撤单
        elif action == ActionType.TERMINATE and username == own:
            approve_itsm_ticket(OperateNodeActionType.WITHDRAW, is_approved=False)
            self.todo.set_terminated(username, action)
        # 只允许审批人通过
        elif action == ActionType.APPROVE and username != own:
            approve_itsm_ticket(OperateNodeActionType.TRANSITION, is_approved=True)
            self.todo.set_success(username, action)
