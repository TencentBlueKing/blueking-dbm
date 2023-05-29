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
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.hadb.client import HADBApi
from backend.db_proxy.constants import SWAGGER_TAG

from ..views import BaseProxyPassViewSet
from .serializers import HADBProxyPassSerializer


class HADBProxyPassViewSet(BaseProxyPassViewSet):
    """
    HADB服务接口的透传视图
    """

    @common_swagger_auto_schema(
        operation_summary=_("[hadb]上报和查询ha的探测切换日志"),
        request_body=HADBProxyPassSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=HADBProxyPassSerializer, url_path="hadb/halogs")
    def ha_logs(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(HADBApi.ha_logs(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[hadb]上报和查询数据库实例的状态"),
        request_body=HADBProxyPassSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=HADBProxyPassSerializer, url_path="hadb/dbstatus")
    def db_status(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(HADBApi.db_status(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[hadb]上报和查询ha服务的状态"),
        request_body=HADBProxyPassSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=HADBProxyPassSerializer, url_path="hadb/hastatus")
    def ha_status(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(HADBApi.ha_status(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[hadb]查询和上报切换队列"),
        request_body=HADBProxyPassSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=HADBProxyPassSerializer, url_path="hadb/switchqueue")
    def switch_queue(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(HADBApi.switch_queue(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[hadb]查询和上报切换日志"),
        request_body=HADBProxyPassSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=HADBProxyPassSerializer, url_path="hadb/switchlogs")
    def switch_logs(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(HADBApi.switch_logs(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[hadb]DBHA切换屏蔽配置"),
        request_body=HADBProxyPassSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=HADBProxyPassSerializer, url_path="hadb/shieldconfig")
    def shieldconfig(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(HADBApi.shieldconfig(params=validated_data))
