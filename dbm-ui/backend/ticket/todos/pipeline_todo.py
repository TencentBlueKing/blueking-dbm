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

from django.db import transaction
from django.utils.translation import ugettext as _

from backend.core import notify
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.ticket import todos
from backend.ticket.constants import TODO_RUNNING_STATUS, TodoStatus, TodoType
from backend.ticket.models import Flow, TodoHistory
from backend.ticket.todos import BaseTodoContext, TodoActionType

logger = logging.getLogger("root")


@dataclass
class PipelineTodoContext(BaseTodoContext):
    root_id: str
    node_id: str


@todos.TodoActorFactory.register(TodoType.INNER_APPROVE)
class PipelineTodo(todos.TodoActor):
    """来自自动化流程中的待办"""

    def _process(self, username, action, params):
        """确认/终止"""
        # 从todo的上下文获取pipeline节点信息
        root_id, node_id = self.context.get("root_id"), self.context.get("node_id")
        engine = BambooEngine(root_id=root_id)

        if action == TodoActionType.TERMINATE:
            self.todo.set_status(username, TodoStatus.DONE_FAILED)
            # 终止时，直接将流程设置为失败
            engine.force_fail_node(node_id, ex_data=_("人工强制失败"))
            return

        res = engine.callback(node_id=node_id, desc="")

        logger.info(
            f"{username} process({action}) pipeline node, root_id:{root_id}, node_id:{node_id}\n"
            f"flow_tree:{engine.get_pipeline_tree_states()}"
        )

        if not res.result:
            logger.error(
                f"{username} process({action}) pipeline node, root_id:{root_id}, node_id:{node_id}\n"
                f"error:{res.exc.args}"
            )

            TodoHistory.objects.create(creator=username, todo=self.todo, action=action)
            raise Exception(",".join(res.exc.args))

        self.todo.set_success(username, action)

    @classmethod
    def create(cls, ticket, flow, root_id, node_id):
        from backend.ticket.models import Todo

        # 创建一条代办，避免同时创建代办导致重复发送通知，用事务进行提交
        with transaction.atomic():
            flow = Flow.objects.select_for_update().get(id=flow.id)

            # 当前不存在待确认的todo，则发送通知
            if not flow.todo_of_flow.filter(type=TodoType.INNER_APPROVE, status__in=TODO_RUNNING_STATUS).count():
                notify.send_msg.apply_async(args=(ticket.id,))

            Todo.objects.create(
                name=_("【{}】流程待确认,是否继续？").format(ticket.get_ticket_type_display()),
                flow=flow,
                ticket=ticket,
                type=TodoType.INNER_APPROVE,
                context=PipelineTodoContext(flow.id, ticket.id, root_id, node_id).to_dict(),
            )
