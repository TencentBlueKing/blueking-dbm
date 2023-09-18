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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.io import ObjectItemSchema, StringItemSchema

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TodoType
from backend.ticket.models import Ticket, Todo
from backend.ticket.todos.pipeline_todo import PipelineTodoContext

logger = logging.getLogger("root")


# 单次回调机制，等待外部调用确认是否继续
class PauseService(BaseService):
    """
    暂停节点，需人工出发继续执行
    """

    __need_schedule__ = True

    def _execute(self, data, parent_data):
        self.log_info("execute PauseService")
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        ticket_id = global_data["uid"]
        ticket = Ticket.objects.get(id=ticket_id)

        # todo：这里假设ticket中不会出现并行的flow
        flow = ticket.current_flow()

        Todo.objects.create(
            name=_("【{}】自动化流程待确认,是否继续？").format(ticket.get_ticket_type_display()),
            flow=flow,
            ticket=ticket,
            type=TodoType.INNER_APPROVE,
            # todo: 待办人暂定为提单人
            operators=[ticket.creator],
            context=PipelineTodoContext(
                flow.id,
                ticket_id,
                self.runtime_attrs.get("root_pipeline_id"),
                self.runtime_attrs.get("id"),
            ).to_dict(),
        )

        self.log_info("pause kwargs: {}".format(kwargs))
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        if callback_data is not None:
            self.log_info("callback_data: {}".format(callback_data))
            data.outputs.callback_data = callback_data
            self.finish_schedule()
        return True

    def inputs_format(self):
        return [
            self.InputItem(
                name=_("描述"), key="description", type="string", schema=StringItemSchema(description="description")
            )
        ]

    def outputs_format(self):
        return [
            self.OutputItem(
                name=_("回调数据"),
                key="callback_data",
                type="object",
                schema=ObjectItemSchema(description="node_callback api with params(dict)", property_schemas={}),
            )
        ]


class PauseComponent(Component):
    name = _("暂停")
    code = "pause"
    bound_service = PauseService
