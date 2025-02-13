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

from backend.db_meta.models.sqlserver_dts import DtsStatus, SqlserverDtsInfo
from backend.ticket import todos
from backend.ticket.constants import TicketFlowStatus, TicketType, TodoStatus, TodoType
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.todos import BaseTodoContext, TodoActionType


@dataclass
class PauseTodoContext(BaseTodoContext):
    pass


@dataclass
class ResourceReplenishTodoContext(BaseTodoContext):
    user: str
    administrators: list


@todos.TodoActorFactory.register(TodoType.APPROVE)
class PauseTodo(todos.TodoActor):
    """来自主流程的待办"""

    @property
    def allow_superuser_process(self):
        # 单据未执行前（待审批、待执行时）超管不拥有特权。规避超管误点的风险
        return False

    def _process(self, username, action, params):
        """确认/终止"""
        if action == TodoActionType.TERMINATE:
            self.todo.set_terminated(username, action)
            return

        self.todo.set_success(username, action)

        # 所有待办完成后，执行后面的flow
        if not self.todo.ticket.todo_of_ticket.exist_unfinished():
            TicketFlowManager(ticket=self.todo.ticket).run_next_flow()

        # 如果是数据迁移单据，更改迁移记录状态信息
        if self.todo.ticket.ticket_type in [TicketType.SQLSERVER_INCR_MIGRATE, TicketType.SQLSERVER_FULL_MIGRATE]:
            dts = SqlserverDtsInfo.objects.get(ticket_id=self.todo.ticket.id)
            dts.status = DtsStatus.Terminated.value
            dts.save()


@todos.TodoActorFactory.register(TodoType.RESOURCE_REPLENISH)
class ResourceReplenishTodo(todos.TodoActor):
    """资源补货的代办"""

    def _process(self, username, action, params):
        """确认/终止"""
        # 终止单据
        if action == TodoActionType.TERMINATE:
            self.todo.set_terminated(username, action)
            return

        # 尝试重新申请资源，申请成功则关闭todo单
        resource_apply_flow = TicketFlowManager(ticket=self.todo.ticket).get_ticket_flow_cls(self.todo.flow.flow_type)(
            self.todo.flow
        )
        resource_apply_flow.retry()

        # 注意这里需要刷新flow字段
        self.todo.refresh_from_db(fields=["flow"])
        if self.todo.flow.status == TicketFlowStatus.SUCCEEDED:
            self.todo.set_success(username, action)


@todos.TodoActorFactory.register(TodoType.INNER_FAILED)
class FailedTodo(todos.TodoActor):
    """来自主流程-失败后待确认"""

    def _process(self, username, action, params):
        # 终止-仅将todo进行终止(任务流程的终止)，确认-关联flow进行重试
        if action == TodoActionType.TERMINATE:
            self.todo.set_status(username, TodoStatus.DONE_FAILED)
        else:
            manager = TicketFlowManager(ticket=self.todo.ticket)
            fail_inner_flow = manager.get_ticket_flow_cls(self.todo.flow.flow_type)(self.todo.flow)
            fail_inner_flow.retry()
