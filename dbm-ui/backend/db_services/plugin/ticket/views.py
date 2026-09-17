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
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from backend.bk_web.swagger import PaginatedResponseSwaggerAutoSchema, common_swagger_auto_schema
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.ticket.serializers import (
    OpenAPIBatchTicketOperateSerializer,
    OpenAPIBkChatProcessTodoResponseSerializer,
    OpenAPIBkChatProcessTodoSerializer,
)
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.ticket.constants import TodoStatus, TodoType
from backend.ticket.exceptions import TodoDuplicateProcessException
from backend.ticket.models import Todo
from backend.ticket.serializers import (
    BatchTodoOperateSerializer,
    FastCreateCloudComponentSerializer,
    RevokeTicketSLZ,
    SensitiveTicketSerializer,
    TicketFlowSerializer,
    TicketSerializer,
    TodoOperateSerializer,
    TodoSerializer,
)
from backend.ticket.todos import TodoActorFactory
from backend.ticket.views import TicketViewSet

logger = logging.getLogger("root")


class TicketApiGwViewSet(BaseOpenAPIViewSet, TicketViewSet):
    serializer_class = TicketSerializer

    def get_permissions(self):
        # bkchat_process_todo 是 bkchat 机器人回调接口，无需鉴权
        if self.action == "bkchat_process_todo":
            return []
        return super().get_permissions()

    @common_swagger_auto_schema(
        operation_summary=_("单据列表"),
        auto_schema=PaginatedResponseSwaggerAutoSchema,
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("批量单据待办处理"),
        request_body=OpenAPIBatchTicketOperateSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=OpenAPIBatchTicketOperateSerializer)
    def batch_process_ticket(self, request, *args, **kwargs):
        return super().batch_process_ticket(request, *args, **kwargs)

    @common_swagger_auto_schema(
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
            return Response({"response_msg": _("暂不支持该类型{}todo的处理").fromat(todo.type), "response_color": "red"})

        # 确认todo，忽略重复操作
        try:
            TodoActorFactory.actor(todo).process(user.username, params["action"], params["params"])
        except TodoDuplicateProcessException:
            pass

        # 根据操作类型获取文案和按钮颜色
        todo.refresh_from_db()
        if todo.status == TodoStatus.DONE_FAILED:
            return Response({"response_msg": _("{} 已终止").format(todo.done_by), "response_color": "red"})
        elif todo.status == TodoStatus.DONE_SUCCESS:
            return Response({"response_msg": _("{} 已确认").format(todo.done_by), "response_color": "green"})

    @common_swagger_auto_schema(
        operation_summary=_("创建单据"),
        responses={status.HTTP_200_OK: TicketSerializer(label=_("创建单据"))},
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("单据终止"),
        request_body=RevokeTicketSLZ(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=RevokeTicketSLZ)
    def revoke_ticket(self, request, *args, **kwargs):
        return super().revoke_ticket(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("批量待办处理"),
        request_body=BatchTodoOperateSerializer(),
        responses={status.HTTP_200_OK: TodoSerializer(many=True)},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=BatchTodoOperateSerializer)
    def batch_process_todo(self, request, *args, **kwargs):
        return super().batch_process_todo(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("创建单据(允许创建敏感单据)"),
        request_body=SensitiveTicketSerializer(),
        responses={status.HTTP_200_OK: SensitiveTicketSerializer(label=_("创建单据(允许创建敏感单据)"))},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=SensitiveTicketSerializer)
    def create_sensitive_ticket(self, request, *args, **kwargs):
        return super().create_sensitive_ticket(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("快速部署云区域组件"),
        request_body=FastCreateCloudComponentSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=FastCreateCloudComponentSerializer)
    def fast_create_cloud_component(self, request, *args, **kwargs):
        return super().fast_create_cloud_component(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("单据详情"),
        responses={status.HTTP_200_OK: TicketSerializer(label=_("单据详情"))},
        tags=[SWAGGER_TAG],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("单据回调"),
        request_body=serializers.Serializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True, permission_classes=[AllowAny])
    def callback(self, request, pk):
        return super().callback(request, pk)

    @common_swagger_auto_schema(
        operation_summary=_("获取单据流程"),
        responses={status.HTTP_200_OK: TicketFlowSerializer(label=_("流程信息"), many=True)},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=True, serializer_class=TicketFlowSerializer)
    def flows(self, request, *args, **kwargs):
        return super().flows(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("待办处理"),
        request_body=TodoOperateSerializer(),
        responses={status.HTTP_200_OK: TodoSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=True, serializer_class=TodoOperateSerializer)
    def process_todo(self, request, *args, **kwargs):
        return super().process_todo(request, *args, **kwargs)
