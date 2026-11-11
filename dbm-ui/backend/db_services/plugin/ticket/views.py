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
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.ticket.serializers import (
    OpenAPIBatchTicketOperateSerializer,
    OpenAPIBkChatProcessTodoResponseSerializer,
    OpenAPIBkChatProcessTodoSerializer,
)
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.ticket.constants import TODO_RUNNING_STATUS, TicketFlowStatus, TodoStatus, TodoType
from backend.ticket.exceptions import TodoDuplicateProcessException
from backend.ticket.models import TicketSnapshot, Todo
from backend.ticket.serializers import TicketSerializer
from backend.ticket.todos import TodoActorFactory
from backend.ticket.views import TicketViewSet

logger = logging.getLogger("root")


class TicketApiGwViewSet(BaseOpenAPIViewSet, TicketViewSet):
    def get_permissions(self):
        # bkchat_process_todo 是 bkchat 机器人回调接口，无需鉴权
        if self.action == "bkchat_process_todo":
            return []
        return super().get_permissions()

    @swagger_auto_schema(
        operation_summary=_("批量单据待办处理"),
        request_body=OpenAPIBatchTicketOperateSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=OpenAPIBatchTicketOperateSerializer)
    def batch_process_ticket(self, request, *args, **kwargs):
        return super().batch_process_ticket(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary=_("待办处理(bkchat专属)"),
        request_body=OpenAPIBkChatProcessTodoSerializer(),
        responses={status.HTTP_200_OK: OpenAPIBkChatProcessTodoResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=OpenAPIBkChatProcessTodoSerializer)
    def bkchat_process_todo(self, request, *args, **kwargs):
        """
        bkchat专属的待办处理，区别主要是返回结构不同
        """
        params = self.params_validate(self.get_serializer_class())
        user = super().get_or_create_user(params["username"])
        todo = Todo.objects.get(id=params["todo_id"])
        if todo.type not in [TodoType.ITSM, TodoType.APPROVE]:
            return Response({"response_msg": _("暂不支持该类型{}todo的处理").format(todo.type), "response_color": "red"})

        # 过期通知：通知发出后节点可能已经结束(审批期间被代为修改、提单人重新编辑后进入新一轮审批)，
        # 此时对旧通知做通过/拒绝属于过期操作，要明确报错，而不是静默返回上一次的处理结果
        flow_status = todo.flow.status if todo.flow_id else None
        if todo.status not in TODO_RUNNING_STATUS and flow_status != TicketFlowStatus.RUNNING:
            return Response({"response_msg": _("该节点状态不符合当前操作，请刷新单据后重试"), "response_color": "red"})

        # 企微卡片带不回版本号时(如按钮 payload 未携带)，按单据当前内容版本补齐，
        # 避免 ITSM 单据的版本校验直接抛"缺少单据内容版本号"
        action_params = dict(params.get("params") or {})
        action_params.setdefault("version", TicketSnapshot.objects.filter(ticket_id=todo.ticket_id).count())

        # 确认todo，忽略重复操作
        try:
            TodoActorFactory.actor(todo).process(user.username, params["action"], action_params)
        except TodoDuplicateProcessException:
            pass

        # 根据操作类型获取文案和按钮颜色
        todo.refresh_from_db()
        if todo.status == TodoStatus.DONE_FAILED:
            return Response({"response_msg": _("{} 已终止").format(todo.done_by), "response_color": "red"})
        elif todo.status == TodoStatus.DONE_SUCCESS:
            return Response({"response_msg": _("{} 已确认").format(todo.done_by), "response_color": "green"})

    @swagger_auto_schema(
        operation_summary=_("创建单据"),
        responses={status.HTTP_200_OK: TicketSerializer(label=_("创建单据"))},
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
