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

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.io import ObjectItemSchema, StringItemSchema

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.models import Ticket
from backend.ticket.todos.pipeline_todo import PipelineTodo

logger = logging.getLogger("root")


def resolve_pause_ticket(uid):
    """
    解析暂停节点关联的单据。
    scene 直驱等场景 uid 可能是非数字字符串，或尚未落库成 Ticket，此时返回 None。
    """
    if uid is None:
        return None
    uid_str = str(uid).strip()
    if not uid_str.isdigit():
        return None
    return Ticket.objects.filter(id=int(uid_str)).first()


# 单次回调机制，等待外部调用确认是否继续
class PauseService(BaseService):
    """
    暂停节点，需人工出发继续执行
    """

    __need_schedule__ = True

    def _execute(self, data, parent_data):
        self.log_info("execute PauseService")
        # 默认需要 schedule；无有效单据时改为直接放行
        self._pass_without_ticket = False
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data") or {}

        ticket = resolve_pause_ticket(global_data.get("uid"))
        if not ticket:
            # scene 直驱 / 无单据：不建 PipelineTodo，也不进入回调等待
            self._pass_without_ticket = True
            self.log_info(_("uid 非有效单据 ID，跳过暂停节点直接放行: {}").format(global_data.get("uid")))
            return True

        flow = ticket.current_flow()
        # 创建一条代办
        PipelineTodo.create(ticket, flow, self.runtime_attrs.get("root_pipeline_id"), self.runtime_attrs.get("id"))

        self.log_info("pause kwargs: {}".format(kwargs))
        return True

    def need_schedule(self):
        if getattr(self, "_pass_without_ticket", False):
            return False
        return super().need_schedule()

    def _schedule(self, data, parent_data, callback_data=None):
        check_result = True
        if callback_data is not None:
            self.log_info("callback_data: {}".format(callback_data))
            data.outputs.callback_data = callback_data

            self.finish_schedule()
        return check_result

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
