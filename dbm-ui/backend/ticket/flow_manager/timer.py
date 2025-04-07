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

import uuid
from datetime import datetime
from typing import Optional, Union

from django.utils import timezone
from django.utils.translation import gettext as _

from backend.ticket import constants
from backend.ticket.constants import TodoType
from backend.ticket.flow_manager.base import BaseTicketFlow
from backend.ticket.models import Flow, Todo
from backend.ticket.tasks.ticket_tasks import TicketTask, apply_ticket_task
from backend.ticket.todos.timer_todo import TimerTodoContext
from backend.utils.basic import get_target_items_from_details
from backend.utils.time import countdown2str, datetime2str, str2datetime


class TimerFlow(BaseTicketFlow):
    """
    内置定时流程，用于定时触发下一个流程，这里的时间用timestamp单位
    当到达指定时间时，会触发两种情况：
    1. 若前面的单据/任务未完成，则定时节点过期，当前节点会变为手动执行
    2. 若当前的单据/节点已完成，则自动触发下一个节点
    """

    def __init__(self, flow_obj: Flow):
        super().__init__(flow_obj=flow_obj)

        self.root_id = flow_obj.flow_obj_id
        # 过期标志
        self.expired_flag = flow_obj.details.get("expired_flag", None)
        # 定时发起时间
        self.run_time = flow_obj.details.get("run_time", datetime2str(datetime.now(timezone.utc)))
        # 定时异步任务id
        self.task_id = flow_obj.details.get("task_id", "")
        # 定时触发时间
        ticket_trigger_time = get_target_items_from_details(obj=self.ticket.details, match_keys=["trigger_time"])[0]
        self.trigger_time = flow_obj.details.get("trigger_time", ticket_trigger_time)

    @property
    def _start_time(self) -> str:
        return datetime2str(self.flow_obj.create_at)

    @property
    def _end_time(self) -> Optional[str]:
        return datetime2str(self.flow_obj.update_at)

    @property
    def _summary(self) -> str:
        run_time, trigger_time = str2datetime(self.run_time), str2datetime(self.trigger_time)
        if self.expired_flag:
            return _("定时时间{}，已超时{}，需手动触发。暂停状态:{}").format(
                self.trigger_time,
                countdown2str(run_time - trigger_time),
                constants.TicketFlowStatus.get_choice_label(self.status),
            )

        now = datetime.now(timezone.utc)
        if trigger_time < now:
            return _("定时节点已触发")

        return _("定时时间{}，倒计时:{}").format(trigger_time, countdown2str(trigger_time - now))

    @property
    def _status(self) -> str:
        trigger_time = str2datetime(self.trigger_time)
        now = datetime.now(timezone.utc)
        # 还未到定时节点，返回pending
        if self.expired_flag is None:
            return constants.TicketFlowStatus.PENDING.value
        # 已过期，但是todo未处理，则返回running
        if self.expired_flag and self.ticket.todo_of_ticket.exist_unfinished():
            return self.flow_obj.update_status(constants.TicketFlowStatus.RUNNING.value)
        # 触发时间晚于当前时间，则返回running
        if trigger_time > now:
            return self.flow_obj.update_status(constants.TicketFlowStatus.RUNNING.value)
        # 其他情况说明已触发，返回succeed，并且标记todo为已处理
        self.flow_obj.todo_of_flow.update(status=constants.TodoStatus.DONE_SUCCESS.value, done_at=now)
        return self.flow_obj.update_status(constants.TicketFlowStatus.SUCCEEDED.value)

    @property
    def _url(self) -> str:
        pass

    def _run(self) -> Union[int, str]:
        timer_uid = f"timer_{uuid.uuid1().hex}"
        task_id = ""

        # 创建一个定时todo TODO: get_or_create好像使得自定义的create方法不生效
        try:
            todo = Todo.objects.get(flow=self.flow_obj, ticket=self.ticket, type=TodoType.TIMER)
        except Todo.DoesNotExist:
            todo = Todo.objects.create(flow=self.flow_obj, ticket=self.ticket, type=TodoType.TIMER)
            todo.context = TimerTodoContext(self.flow_obj.id, self.ticket.id).to_dict()

        # 如果触发时间已经过期，则变为手动触发，否则为定时触发
        run_time, trigger_time = str2datetime(self.run_time), str2datetime(self.trigger_time)
        if run_time >= trigger_time:
            todo.type = TodoType.APPROVE
            todo.name = (_("【{}】流程待确认，是否继续？").format(self.ticket.get_ticket_type_display()),)
            self.expired_flag = True
        else:
            todo.name = _("【{}】流程定时中").format(self.ticket.get_ticket_type_display())
            self.expired_flag = False
            task_id = apply_ticket_task(
                ticket_id=self.ticket.id,
                func_name=TicketTask.run_next_flow.__name__,
                eta=trigger_time,
            ).id

        # 更新flow的状态信息
        todo.save()
        self.flow_obj.update_details(
            expired_flag=self.expired_flag, run_time=self.run_time, trigger_time=self.trigger_time, task_id=task_id
        )
        return timer_uid
