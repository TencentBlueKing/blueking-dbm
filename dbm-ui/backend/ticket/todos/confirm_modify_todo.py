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
from dataclasses import dataclass

from django.utils.translation import gettext as _

from backend.ticket import todos
from backend.ticket.constants import FlowContext, TodoType
from backend.ticket.todos import BaseTodoContext, TodoActionType


@dataclass
class ConfirmModifyTodoContext(BaseTodoContext):
    pass


@todos.TodoActorFactory.register(TodoType.CONFIRM_MODIFY)
class ConfirmModifyTodo(todos.TodoActor):
    """待确认修改的待办，处理人为提单人"""

    @property
    def allow_superuser_process(self):
        # 单据未执行前超管不拥有特权，规避超管误点风险
        return False

    def _process(self, username, action, params):
        # 终止单据
        if action == TodoActionType.TERMINATE:
            self.todo.set_terminated(username, action)
            return

        # 确认修改：写入出口词并继续执行后续流程
        self.todo.flow.update_context(**{FlowContext.EXIT_WORD.value: _("确认无误")})
        self.todo.set_success(username, action)

        # 所有待办完成后，执行后面的flow
        if not self.todo.ticket.todo_of_ticket.exist_unfinished():
            from backend.ticket.flow_manager.manager import TicketFlowManager

            TicketFlowManager(ticket=self.todo.ticket).run_next_flow()
