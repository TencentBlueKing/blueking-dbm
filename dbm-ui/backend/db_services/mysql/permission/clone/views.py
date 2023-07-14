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

from django.http.response import HttpResponse
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.permission.clone.dataclass import CloneMeta
from backend.db_services.mysql.permission.clone.handlers import CloneHandler
from backend.db_services.mysql.permission.clone.serializers import (
    GetExcelCloneInfoSerializer,
    PreCheckCloneResponseSerializer,
    PreCheckCloneSerializer,
    PreCheckExcelCloneResponseSerializer,
    PreCheckExcelCloneSerializere,
)
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission

SWAGGER_TAG = "db_services/permission/clone"


class DBCloneViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    def _view_common_handler(
        self, request, bk_biz_id: int, meta: Type[CloneMeta], func: str
    ) -> Union[Response, HttpResponse]:
        """
        - 视图通用处理函数, 方便统一管理
        :param request: request请求
        :param bk_biz_id: 业务ID
        :param meta: 元信息数据结构
        :param func: handler的回调函数名称
        """

        validated_data = self.params_validate(self.get_serializer_class(), context={"bk_biz_id": bk_biz_id})
        base_info = {
            "bk_biz_id": bk_biz_id,
            "operator": request.user.username,
            "clone_type": validated_data["clone_type"],
            "account_type": validated_data.pop("account_type", None),
            "context": {},
        }
        meta_init_data = meta.from_dict(validated_data)
        handler_result = getattr(CloneHandler(**base_info), func)(meta_init_data)
        if isinstance(handler_result, HttpResponse):
            return handler_result

        return Response(handler_result)

    @common_swagger_auto_schema(
        operation_summary=_("权限克隆前置检查"),
        request_body=PreCheckCloneSerializer(),
        responses={status.HTTP_200_OK: PreCheckCloneResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PreCheckCloneSerializer)
    def pre_check_clone(self, request, bk_biz_id):
        return self._view_common_handler(request, bk_biz_id, CloneMeta, CloneHandler.pre_check_clone.__name__)

    @common_swagger_auto_schema(
        operation_summary=_("权限克隆excel前置检查"),
        request_body=PreCheckExcelCloneSerializere(),
        responses={status.HTTP_200_OK: PreCheckExcelCloneResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PreCheckExcelCloneSerializere)
    def pre_check_excel_clone(self, request, bk_biz_id):
        return self._view_common_handler(request, bk_biz_id, CloneMeta, CloneHandler.pre_check_excel_clone.__name__)

    @common_swagger_auto_schema(
        operation_summary=_("获得权限克隆信息excel文件"),
        query_serializer=GetExcelCloneInfoSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetExcelCloneInfoSerializer)
    def get_clone_info_excel(self, request, bk_biz_id):
        return self._view_common_handler(request, bk_biz_id, CloneMeta, CloneHandler.get_clone_info_excel.__name__)
