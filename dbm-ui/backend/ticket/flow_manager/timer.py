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
        self.expired_flag = flow_obj.details.get("expired_flag", None)
        self.run_time = flow_obj.details.get("run_time", datetime2str(datetime.now(timezone.utc)))
        self.trigger_time = get_target_items_from_details(obj=self.ticket.details, match_keys=["trigger_time"])[0]

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
                constants.TicketStatus.get_choice_label(self.status),
            )

        now = datetime.now(timezone.utc)
        if trigger_time < now:
            return _("定时节点已触发")

        return _("定时时间{}，倒计时:{}").format(trigger_time, countdown2str(trigger_time - now))

    @property
    def _status(self) -> str:
        trigger_time = str2datetime(self.trigger_time)
        if self.expired_flag is None:
            return constants.TicketStatus.PENDING.value

        if self.expired_flag and self.ticket.todo_of_ticket.exist_unfinished():
            self.flow_obj.update_status(constants.TicketStatus.RUNNING.value)
            return constants.TicketStatus.RUNNING.value

        if trigger_time > datetime.now(timezone.utc):
            self.flow_obj.update_status(constants.TicketStatus.RUNNING.value)
            return constants.TicketStatus.RUNNING.value

        self.flow_obj.update_status(constants.TicketStatus.SUCCEEDED.value)
        return constants.TicketStatus.SUCCEEDED.value

    @property
    def _url(self) -> str:
        pass

    def _run(self) -> Union[int, str]:
        timer_uid = f"timer_{uuid.uuid1().hex}"

        # 如果触发时间已经过期，则变为手动触发，否则变为定时触发
        run_time, trigger_time = str2datetime(self.run_time), str2datetime(self.trigger_time)
        if run_time >= trigger_time:
            from backend.ticket.todos.pause_todo import PauseTodoContext

            self.expired_flag = True
            Todo.objects.create(
                name=_("【{}】定时流程待确认,是否继续？").format(self.ticket.get_ticket_type_display()),
                flow=self.flow_obj,
                ticket=self.ticket,
                type=TodoType.APPROVE,
                operators=[self.ticket.creator],
                context=PauseTodoContext(self.flow_obj.id, self.ticket.id).to_dict(),
            )
        else:
            self.expired_flag = False
            apply_ticket_task(
                ticket_id=self.ticket.id,
                func_name=TicketTask.run_next_flow.__name__,
                eta=trigger_time,
            )

        # 更新flow的状态信息
        self.flow_obj.update_details(expired_flag=self.expired_flag, run_time=self.run_time)
        return timer_uid
