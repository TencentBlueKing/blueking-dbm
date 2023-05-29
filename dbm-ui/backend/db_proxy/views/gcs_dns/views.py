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
from backend.components.gcs_dns.client import GcsDnsApi
from backend.db_proxy.constants import SWAGGER_TAG

from ..views import BaseProxyPassViewSet
from .serializers import (
    BatchPostDomainResponseSerializerte,
    BatchPostDomainSerializer,
    DeleteDomainResponseSerializer,
    DeleteDomainSerializer,
    GetAllDomainListResponseSerializer,
    GetAllDomainListSerializer,
    GetDomainResponseSerializer,
    GetDomainSerializer,
    PostDoaminResponseSerializerte,
    PostDoaminSerializer,
    PutDoaminResponseSerializerte,
    PutDoaminSerializer,
)


class GcsDnsProxyPassViewSet(BaseProxyPassViewSet):
    """
    GcsDns接口的透传视图
    """

    def get_permissions(self):
        # TODO: 内部服务接口，是否需要鉴权？
        return [AllowAny()]

    @common_swagger_auto_schema(
        operation_summary=_("[gcsdns]获取所有ip、域名关系"),
        request_body=GetAllDomainListSerializer(),
        responses={status.HTTP_200_OK: GetAllDomainListResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=GetAllDomainListSerializer, url_path="dns/domain/all")
    def get_all_domain_list(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(GcsDnsApi.get_all_domain_list(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[gcsdns]获取域名映射关系"),
        request_body=GetDomainSerializer(),
        responses={status.HTTP_200_OK: GetDomainResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=GetDomainSerializer, url_path="dns/domain/get")
    def get_domain(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(GcsDnsApi.get_domain(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[gcsdns]批量更新域名映射关系"),
        request_body=BatchPostDomainSerializer(),
        responses={status.HTTP_200_OK: BatchPostDomainResponseSerializerte()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=BatchPostDomainSerializer, url_path="dns/domain/batch")
    def batch_post_domain(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(GcsDnsApi.batch_update_domain(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[gcsdns]更新域名映射关系"),
        request_body=PostDoaminSerializer(),
        responses={status.HTTP_200_OK: PostDoaminResponseSerializerte()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PostDoaminSerializer, url_path="dns/domain/post")
    def post_domain(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(GcsDnsApi.update_domain(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[gcsdns]删除域名映射"),
        request_body=DeleteDomainSerializer(),
        responses={status.HTTP_200_OK: DeleteDomainResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["DELETE"], detail=False, serializer_class=DeleteDomainSerializer, url_path="dns/domain/delete")
    def delete_domain(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(GcsDnsApi.delete_domain(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("[gcsdns]新增域名映射关系"),
        request_body=PutDoaminSerializer(),
        responses={status.HTTP_200_OK: PutDoaminResponseSerializerte()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["PUT"], detail=False, serializer_class=PutDoaminSerializer, url_path="dns/domain/put")
    def put_domain(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(GcsDnsApi.create_domain(params=validated_data))
