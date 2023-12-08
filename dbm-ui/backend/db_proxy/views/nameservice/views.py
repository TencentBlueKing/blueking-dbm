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
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.db_name_service.client import NameServiceApi
from backend.db_proxy.constants import SWAGGER_TAG
from backend.db_proxy.views.nameservice.serializers import (
    CLBDeregisterPartTargetSerializer,
    CLBGetTargetPrivateIps,
    PolarisDescribeTargetsSerializer,
    PolarisUnbindPartTargetsSerializer,
)
from backend.db_proxy.views.views import BaseProxyPassViewSet


class NameServiceProxyPassViewSet(BaseProxyPassViewSet):
    """
    name service相关透传接口视图
    """

    @common_swagger_auto_schema(
        operation_summary=_("[name service]clb解绑部分后端主机"),
        request_body=CLBDeregisterPartTargetSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=CLBDeregisterPartTargetSerializer,
        url_path="nameservice/clb_deregister_part_target",
    )
    def clb_deregister_part_target(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(NameServiceApi.clb_deregister_part_target(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[name service]获取clb已绑定后端主机的IP"),
        request_body=CLBGetTargetPrivateIps(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=CLBGetTargetPrivateIps,
        url_path="nameservice/clb_get_target_private_ips",
    )
    def clb_get_target_private_ips(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(NameServiceApi.clb_get_target_private_ips(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[name service]获取polaris后端主机信息"),
        request_body=PolarisDescribeTargetsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=PolarisDescribeTargetsSerializer,
        url_path="nameservice/polaris_describe_targets",
    )
    def polaris_describe_targets(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(NameServiceApi.polaris_describe_targets(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[name service]polaris解绑部分后端主机"),
        request_body=PolarisUnbindPartTargetsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=PolarisUnbindPartTargetsSerializer,
        url_path="nameservice/polaris_unbind_part_targets",
    )
    def polaris_unbind_part_targets(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(NameServiceApi.polaris_unbind_part_targets(validated_data))
