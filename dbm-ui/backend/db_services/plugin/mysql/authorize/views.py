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

from django.utils.translation import ugettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.permission.authorize.handlers import AuthorizeHandler
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.mysql.authorize.serializers import (
    AuthorizeApplySerializer,
    QueryAuthorizeApplySerializer,
)
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission


class AuthorizePluginViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("第三方权限申请(兼容GCS)"),
        request_body=AuthorizeApplySerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=AuthorizeApplySerializer)
    def authorize_apply(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        handler = AuthorizeHandler(bk_biz_id=0, operator=request.user.username)
        return Response(handler.authorize_apply(**data))

    @common_swagger_auto_schema(
        operation_summary=_("查询第三方权限申请结果(兼容GCS)"),
        query_serializer=QueryAuthorizeApplySerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=QueryAuthorizeApplySerializer)
    def query_authorize_apply_result(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        handler = AuthorizeHandler(bk_biz_id=0, operator=request.user.username)
        return Response(handler.query_authorize_apply_result(**data))
