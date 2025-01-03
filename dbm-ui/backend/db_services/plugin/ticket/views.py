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
from backend.ticket.constants import TodoStatus, TodoType
from backend.ticket.exceptions import TodoDuplicateProcessException
from backend.ticket.handler import TicketHandler
from backend.ticket.models import Todo
from backend.ticket.todos import TodoActorFactory

logger = logging.getLogger("root")


class TicketViewSet(BaseOpenAPIViewSet):
    @swagger_auto_schema(
        operation_summary=_("批量单据待办处理"),
        request_body=OpenAPIBatchTicketOperateSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=OpenAPIBatchTicketOperateSerializer)
    def batch_process_ticket(self, request, *args, **kwargs):
        params = self.params_validate(self.get_serializer_class())
        return Response(TicketHandler.batch_process_ticket(**params))

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

        todo = Todo.objects.get(id=params["todo_id"])
        if todo.type not in [TodoType.ITSM, TodoType.APPROVE]:
            return Response({"response_msg": _("暂不支持该类型{}todo的处理").fromat(todo.type), "response_color": "red"})

        # 确认todo，忽略重复操作
        try:
            TodoActorFactory.actor(todo).process(params["username"], params["action"], params["params"])
        except TodoDuplicateProcessException:
            pass

        # 根据操作类型获取文案和按钮颜色
        todo.refresh_from_db()
        if todo.status == TodoStatus.DONE_FAILED:
            return Response({"response_msg": _("{} 已终止").format(todo.done_by), "response_color": "red"})
        elif todo.status == TodoStatus.DONE_SUCCESS:
            return Response({"response_msg": _("{} 已确认").format(todo.done_by), "response_color": "green"})
