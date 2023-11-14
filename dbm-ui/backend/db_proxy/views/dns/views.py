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
from backend.components.dns.client import DnsApi
from backend.db_proxy.constants import SWAGGER_TAG
from backend.db_proxy.views.dns import serializers
from backend.db_proxy.views.views import BaseProxyPassViewSet


class DnsProxyPassViewSet(BaseProxyPassViewSet):
    """
    Dns接口的透传视图
    """

    def get_permissions(self):
        # TODO: 内部服务接口，是否需要鉴权？
        return [AllowAny()]

    @common_swagger_auto_schema(
        operation_summary=_("[dns]获取所有ip、域名关系"),
        request_body=serializers.GetAllDomainListSerializer(),
        responses={status.HTTP_200_OK: serializers.GetAllDomainListResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=serializers.GetAllDomainListSerializer,
        url_path="dns/domain/all",
    )
    def get_all_domain_list(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DnsApi.get_all_domain_list(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[dns]获取域名映射关系"),
        request_body=serializers.GetDomainSerializer(),
        responses={status.HTTP_200_OK: serializers.GetDomainResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"], detail=False, serializer_class=serializers.GetDomainSerializer, url_path="dns/domain/get"
    )
    def get_domain(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DnsApi.get_domain(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[dns]批量更新域名映射关系"),
        request_body=serializers.BatchPostDomainSerializer(),
        responses={status.HTTP_200_OK: serializers.BatchPostDomainResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=serializers.BatchPostDomainSerializer,
        url_path="dns/domain/batch",
    )
    def batch_post_domain(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DnsApi.batch_update_domain(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[dns]更新域名映射关系"),
        request_body=serializers.PostDomainSerializer(),
        responses={status.HTTP_200_OK: serializers.PostDomainResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"], detail=False, serializer_class=serializers.PostDomainSerializer, url_path="dns/domain/post"
    )
    def post_domain(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DnsApi.update_domain(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[dns]删除域名映射"),
        request_body=serializers.DeleteDomainSerializer(),
        responses={status.HTTP_200_OK: serializers.DeleteDomainResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["DELETE"],
        detail=False,
        serializer_class=serializers.DeleteDomainSerializer,
        url_path="dns/domain/delete",
    )
    def delete_domain(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DnsApi.delete_domain(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[dns]新增域名映射关系"),
        request_body=serializers.PutDomainSerializer(),
        responses={status.HTTP_200_OK: serializers.PutDomainResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["PUT"], detail=False, serializer_class=serializers.PutDomainSerializer, url_path="dns/domain/put")
    def put_domain(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DnsApi.create_domain(params=validated_data))
