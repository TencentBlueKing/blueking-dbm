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
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.dbconfig.client import DBConfigApi
from backend.db_proxy.constants import SWAGGER_TAG

from ..views import BaseProxyPassViewSet
from .serializers import (
    BatchGetConfItemResponseSerializer,
    BatchGetConfItemSerializer,
    QueryConfItemResponseSerializer,
    QueryConfItemSerializer,
)


class DBConfigProxyPassViewSet(BaseProxyPassViewSet):
    """
    DBConfig接口的透传视图
    """

    def get_permissions(self):
        # TODO: 内部服务接口，是否需要鉴权？
        return [AllowAny()]

    @common_swagger_auto_schema(
        operation_summary=_("[dbconfig]查询配置项列表"),
        request_body=QueryConfItemSerializer(),
        responses={status.HTTP_200_OK: QueryConfItemResponseSerializer},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"], detail=False, serializer_class=QueryConfItemSerializer, url_path="bkconfig/v1/confitem/query"
    )
    def query_conf_item(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response([DBConfigApi.query_conf_item(params=validated_data)])

    @common_swagger_auto_schema(
        operation_summary=_("[dbconfig]批量获取多个对象的某一配置项"),
        request_body=BatchGetConfItemSerializer(),
        responses={status.HTTP_200_OK: BatchGetConfItemResponseSerializer},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=BatchGetConfItemSerializer,
        url_path="bkconfig/v1/confitem/batchget",
    )
    def batch_get_conf_item(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBConfigApi.batch_get_conf_item(params=validated_data))
