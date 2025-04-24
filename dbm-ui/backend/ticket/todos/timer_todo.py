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
import signal
from dataclasses import dataclass
from datetime import datetime, timezone

from celery import current_app
from django.utils.translation import gettext as _

from backend.ticket import todos
from backend.ticket.constants import TicketFlowStatus, TodoType
from backend.ticket.exceptions import TicketTaskTriggerException
from backend.ticket.todos import BaseTodoContext, TodoActionType
from backend.utils.time import datetime2str

logger = logging.getLogger("root")


@dataclass
class TimerTodoContext(BaseTodoContext):
    remark: str = ""
    action: TodoActionType = ""


@todos.TodoActorFactory.register(TodoType.TIMER)
class TimerTodo(todos.TodoActor):
    """来自定时中的TODO"""

    def _process(self, username, action, params):
        from backend.ticket.flow_manager.manager import TicketFlowManager
        from backend.ticket.flow_manager.timer import TimerFlow

        flow = self.todo.flow
        ticket = self.todo.ticket
        now = datetime2str(datetime.now(timezone.utc))

        if flow.status != TicketFlowStatus.RUNNING or not flow.details.get("task_id"):
            raise TicketTaskTriggerException(_("该定时任务尚未启动或者已经过期"))

        # 无论操作是怎样，都需要终止原来的定时任务
        current_app.control.revoke(flow.details["task_id"], terminate=True, signal=signal.SIGKILL)

        if action == TodoActionType.TERMINATE:
            self.todo.context.update(remark=_("{}终止了定时任务").format(username), action=action)
            self.todo.set_terminated(username, action)
        elif action == TodoActionType.SKIP:
            self.todo.context.update(remark=_("原定时时间: {}").format(flow.details["trigger_time"]), action=action)
            self.todo.set_success(username, action)
            # 将触发时间更新为现在，相当于立刻触发
            flow.update_details(trigger_time=now)
            TicketFlowManager(ticket).run_next_flow()
        elif action == TodoActionType.CHANGE:
            old_trigger_time, new_trigger_time = flow.details["trigger_time"], params["trigger_time"]
            self.todo.context.update(remark=_("由{}修改为{}").format(old_trigger_time, new_trigger_time), action=action)
            self.todo.done_by = username
            self.todo.save()
            # 更新run_time和trigger_time，并重新触发
            flow.update_details(trigger_time=new_trigger_time, run_time=now, task_id="", expired_flag=None)
            TimerFlow(flow).retry()
