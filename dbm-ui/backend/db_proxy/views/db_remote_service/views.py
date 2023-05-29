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
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import DRSApi
from backend.db_proxy.constants import SWAGGER_TAG
from backend.db_proxy.views.db_remote_service.serializers import RPCResponseSerializer, RPCSerializer
from backend.db_proxy.views.views import BaseProxyPassViewSet


class DRSApiProxyPassViewSet(BaseProxyPassViewSet):
    """
    DBMeta接口的透传视图
    """

    @common_swagger_auto_schema(
        operation_summary=_("[db-remote-service]SQL远程执行"),
        request_body=RPCSerializer(),
        responses={status.HTTP_200_OK: RPCResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=RPCSerializer, url_path="drs/mysql/rpc")
    def rpc(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DRSApi.rpc(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[db-remote-service]Proxy SQL远程执行"),
        request_body=RPCSerializer(),
        responses={status.HTTP_200_OK: RPCResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=RPCSerializer, url_path="drs/proxy-admin/rpc")
    def proxyrpc(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DRSApi.proxyrpc(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[db-remote-service]sqlserver SQL远程执行"),
        request_body=RPCSerializer(),
        responses={status.HTTP_200_OK: RPCResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=RPCSerializer, url_path="drs/sqlserver/rpc")
    def sqlserverrpc(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DRSApi.sqlserver_rpc(params=validated_data))
