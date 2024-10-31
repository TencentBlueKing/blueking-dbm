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

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import DnsApi
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission
from backend.legacy.serializers import CreateDNSSerializer, DeleteDNSSerializer

SWAGGER_TAG = ["legacy"]


class DnsViewSet(viewsets.SystemViewSet):
    def get_default_permission_class(self) -> list:
        return [ResourceActionPermission([ActionEnum.GLOBAL_MANAGE])]

    @common_swagger_auto_schema(operation_summary=_("创建 DNS"), tags=SWAGGER_TAG, request_body=CreateDNSSerializer())
    @action(methods=["PUT"], detail=False, serializer_class=CreateDNSSerializer)
    def create_domain(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(DnsApi.create_domain(data))

    @common_swagger_auto_schema(operation_summary=_("删除 DNS"), tags=SWAGGER_TAG, request_body=CreateDNSSerializer())
    @action(methods=["DELETE"], detail=False, serializer_class=DeleteDNSSerializer)
    def delete_domain(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(DnsApi.delete_domain(data))
