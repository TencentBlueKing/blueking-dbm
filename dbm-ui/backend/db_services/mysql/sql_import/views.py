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
from typing import Type, Union

from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.sql_import.dataclass import SemanticOperateMeta, SQLExecuteMeta, SQLMeta
from backend.db_services.mysql.sql_import.handlers import SQLHandler
from backend.db_services.mysql.sql_import.serializers import (
    DeleteUserSemanticListSerializer,
    GetUserSemanticListResponseSerializer,
    GetUserSemanticListSerializer,
    QuerySemanticDataResponseSerializer,
    QuerySemanticDataSerializer,
    QuerySQLUserConfigResponseSerializer,
    QuerySQLUserConfigSerializer,
    RevokeSemanticCheckResponseSerializer,
    RevokeSemanticCheckSerializer,
    SQLGrammarCheckResponseSerializer,
    SQLGrammarCheckSerializer,
    SQLSemanticCheckResponseSerializer,
    SQLSemanticCheckSerializer,
    SQLUserConfigSerializer,
)
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.taskflow import TaskFlowPermission
from backend.iam_app.handlers.drf_perm.ticket import CreateTicketPermission
from backend.ticket.constants import TicketType

SWAGGER_TAG = "db_services/sql_import"


class SQLImportViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        if self.action == "semantic_check":
            cluster_type = self.request.data["cluster_type"]
            ticket_type = getattr(TicketType, f"{cluster_type.upper()}_IMPORT_SQLFILE")
            return [CreateTicketPermission(ticket_type)]
        elif self.action == "revoke_semantic_check":
            return [TaskFlowPermission([ActionEnum.FLOW_DETAIL], ResourceEnum.TASKFLOW)]
        elif self.action == "get_user_semantic_tasks":
            return []

        return [DBManagePermission()]

    def _view_common_handler(
        self,
        request,
        bk_biz_id: int,
        meta: Union[Type[SQLMeta], Type[SQLExecuteMeta], Type[SemanticOperateMeta]],
        func: str,
    ) -> Response:
        """
        - 视图通用处理函数, 方便统一管理
        :param request: request请求
        :param bk_biz_id: 业务ID
        :param meta: 元信息数据结构
        :param func: handler的回调函数名称
        """

        validated_data = self.params_validate(self.get_serializer_class())
        cluster_type = validated_data.pop("cluster_type", None)
        base_info = {"bk_biz_id": bk_biz_id, "context": {"user": request.user.username}, "cluster_type": cluster_type}
        return Response(getattr(SQLHandler(**base_info), func)(**validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("sql语法检查"),
        request_body=SQLGrammarCheckSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: SQLGrammarCheckResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=SQLGrammarCheckSerializer)
    def grammar_check(self, request, bk_biz_id):
        return self._view_common_handler(request, bk_biz_id, SQLMeta, SQLHandler.grammar_check.__name__)

    @common_swagger_auto_schema(
        operation_summary=_("sql语义检查"),
        request_body=SQLSemanticCheckSerializer(),
        responses={status.HTTP_200_OK: SQLSemanticCheckResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=SQLSemanticCheckSerializer)
    def semantic_check(self, request, bk_biz_id):
        return self._view_common_handler(request, bk_biz_id, SQLExecuteMeta, SQLHandler.semantic_check.__name__)

    @common_swagger_auto_schema(
        operation_summary=_("改变用户流程配置"),
        request_body=SQLUserConfigSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=SQLUserConfigSerializer)
    def deploy_user_config(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, SemanticOperateMeta, SQLHandler.deploy_user_config.__name__
        )

    @common_swagger_auto_schema(
        operation_summary=_("查询用户流程配置"),
        query_serializer=QuerySQLUserConfigSerializer(),
        responses={status.HTTP_200_OK: QuerySQLUserConfigResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=QuerySQLUserConfigSerializer)
    def query_user_config(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, SemanticOperateMeta, SQLHandler.query_user_config.__name__
        )

    @common_swagger_auto_schema(
        operation_summary=_("获取用户语义检查任务列表"),
        query_serializer=GetUserSemanticListSerializer(),
        responses={status.HTTP_200_OK: GetUserSemanticListResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetUserSemanticListSerializer)
    def get_user_semantic_tasks(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, SemanticOperateMeta, SQLHandler.get_user_semantic_tasks.__name__
        )

    @common_swagger_auto_schema(
        operation_summary=_("删除用户语义检查任务列表"),
        request_body=DeleteUserSemanticListSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["DELETE"], detail=False, serializer_class=DeleteUserSemanticListSerializer)
    def delete_user_semantic_tasks(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, SemanticOperateMeta, SQLHandler.delete_user_semantic_tasks.__name__
        )

    @common_swagger_auto_schema(
        operation_summary=_("终止语义检查流程"),
        request_body=RevokeSemanticCheckSerializer(),
        responses={status.HTTP_200_OK: RevokeSemanticCheckResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=RevokeSemanticCheckSerializer)
    def revoke_semantic_check(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, SemanticOperateMeta, SQLHandler.revoke_semantic_check.__name__
        )

    @common_swagger_auto_schema(
        operation_summary=_("根据语义执行id查询语义执行的数据"),
        request_body=QuerySemanticDataSerializer(),
        responses={status.HTTP_200_OK: QuerySemanticDataResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=QuerySemanticDataSerializer)
    def query_semantic_data(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, SemanticOperateMeta, SQLHandler.query_semantic_data.__name__
        )
