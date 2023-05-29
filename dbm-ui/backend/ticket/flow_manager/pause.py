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
from typing import Optional, Union

from django.utils.translation import gettext as _

from backend.ticket import constants
from backend.ticket.constants import TodoType
from backend.ticket.flow_manager.base import BaseTicketFlow
from backend.ticket.models import Flow, Todo
from backend.utils.time import datetime2str


class PauseFlow(BaseTicketFlow):
    """
    内置暂停流程，用于用户确认执行下一步
    - 调整：绑定待办
    """

    def __init__(self, flow_obj: Flow):
        self.root_id = flow_obj.flow_obj_id
        super().__init__(flow_obj=flow_obj)

    @property
    def _start_time(self) -> str:
        return datetime2str(self.flow_obj.create_at)

    @property
    def _end_time(self) -> Optional[str]:
        return datetime2str(self.flow_obj.update_at)

    @property
    def _summary(self) -> str:
        return _("暂停状态{status_display}").format(status_display=constants.TicketStatus.get_choice_label(self.status))

    @property
    def _status(self) -> str:
        if self.ticket.todo_of_ticket.exist_unfinished():
            self.flow_obj.update_status(constants.TicketFlowStatus.RUNNING)
            return constants.TicketStatus.RUNNING.value

        self.flow_obj.update_status(constants.TicketFlowStatus.SUCCEEDED)
        return constants.TicketStatus.SUCCEEDED.value

    @property
    def _url(self) -> str:
        pass

    def _run(self) -> Union[int, str]:
        pause_uid = f"pause_{uuid.uuid1().hex}"

        # 创建待办
        from backend.ticket.todos.pause_todo import PauseTodoContext

        Todo.objects.create(
            name=_("【{}】流程待确认，是否继续？").format(self.ticket.get_ticket_type_display()),
            flow=self.flow_obj,
            ticket=self.ticket,
            type=TodoType.APPROVE,
            # TODO: 暂时设置为提单人
            operators=[self.ticket.creator],
            context=PauseTodoContext(self.flow_obj.id, self.ticket.id).to_dict(),
        )

        return pause_uid
