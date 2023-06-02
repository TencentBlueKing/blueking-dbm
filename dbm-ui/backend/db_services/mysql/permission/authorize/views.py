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
from backend.db_services.mysql.permission.authorize.dataclass import (
    AuthorizeMeta,
    ExcelAuthorizeMeta,
    HostInAuthorizeFilterMeta,
)
from backend.db_services.mysql.permission.authorize.handlers import AuthorizeHandler
from backend.db_services.mysql.permission.authorize.serializers import (
    ExcelAuthorizeRulesErrorSerializer,
    GetExcelAuthorizeRulesInfoSerializer,
    GetHostInAuthorizeSerializer,
    GetOnlineMySQLRulesSerializer,
    PreChecExcelAuthorizeRulesResponseSerializer,
    PreCheckAuthorizeRulesSerializer,
    PreCheckExcelAuthorizeRulesResponseSerializer,
    PreCheckExcelAuthorizeRulesSerializer,
)
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission

SWAGGER_TAG = "db_services/permission/authorize"


class DBAuthorizeViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    def _view_common_handler(
        self,
        request,
        bk_biz_id: int,
        meta: Union[Type[AuthorizeMeta], Type[ExcelAuthorizeMeta], Type[HostInAuthorizeFilterMeta]],
        func: str,
    ) -> Union[Response, HttpResponse]:
        """
        - 视图通用处理函数, 方便统一管理
        :param request: request请求
        :param bk_biz_id: 业务ID
        :param meta: 元信息数据结构
        :param func: handler的回调函数名称
        """

        base_info = {"bk_biz_id": bk_biz_id, "operator": request.user.username}
        validated_data = self.params_validate(self.get_serializer_class())
        meta_init_data = meta.from_dict(validated_data)
        handler_result = getattr(AuthorizeHandler(**base_info), func)(meta_init_data)
        if isinstance(handler_result, HttpResponse):
            return handler_result

        return Response(handler_result)

    @common_swagger_auto_schema(
        operation_summary=_("规则前置检查"),
        request_body=PreCheckAuthorizeRulesSerializer(),
        responses={status.HTTP_200_OK: PreChecExcelAuthorizeRulesResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PreCheckAuthorizeRulesSerializer)
    def pre_check_rules(self, request, bk_biz_id):
        return self._view_common_handler(request, bk_biz_id, AuthorizeMeta, AuthorizeHandler.pre_check_rules.__name__)

    @common_swagger_auto_schema(
        operation_summary=_("excel规则前置检查"),
        request_body=PreCheckExcelAuthorizeRulesSerializer(),
        responses={status.HTTP_200_OK: PreCheckExcelAuthorizeRulesResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PreCheckExcelAuthorizeRulesSerializer)
    def pre_check_excel_rules(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, ExcelAuthorizeMeta, AuthorizeHandler.pre_check_excel_rules.__name__
        )

    @common_swagger_auto_schema(
        operation_summary=_("获得授权信息excel文件"),
        query_serializer=GetExcelAuthorizeRulesInfoSerializer(),
        responses={status.HTTP_200_OK: ExcelAuthorizeRulesErrorSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetExcelAuthorizeRulesInfoSerializer)
    def get_authorize_info_excel(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, ExcelAuthorizeMeta, AuthorizeHandler.get_authorize_info_excel.__name__
        )

    @common_swagger_auto_schema(
        operation_summary=_("现网授权查询(暂搁置)"),
        responses={status.HTTP_200_OK: GetOnlineMySQLRulesSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False)
    def get_online_rules(self, request, bk_biz_id):
        return Response(AuthorizeHandler(bk_biz_id).get_online_rules())

    @common_swagger_auto_schema(
        operation_summary=_("查询授权主机的信息"),
        query_serializer=GetHostInAuthorizeSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetHostInAuthorizeSerializer)
    def get_host_in_authorize(self, request, bk_biz_id):
        return self._view_common_handler(
            request, bk_biz_id, HostInAuthorizeFilterMeta, AuthorizeHandler.get_host_in_authorize.__name__
        )
