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
from drf_yasg.openapi import Response as yasg_response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend import env
from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DEFAULT_SETTINGS
from backend.configuration.models.system import SystemSettings
from backend.configuration.serializers import SystemSettingsSerializer

tags = [_("系统设置")]


class SystemSettingsViewSet(viewsets.AuditedModelViewSet):
    """系统设置视图"""

    serializer_class = SystemSettingsSerializer
    queryset = SystemSettings.objects.all()
    # permission_classes 管理员
    filter_fields = {
        "key": ["exact"],
        "type": ["exact"],
        "id": ["exact"],
    }

    def _get_custom_permissions(self):
        return []

    @common_swagger_auto_schema(
        operation_summary=_("系统设置列表"),
        responses={status.HTTP_200_OK: SystemSettingsSerializer(_("系统设置"), many=True)},
        tags=tags,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("系统设置键值映射表"),
        responses={
            status.HTTP_200_OK: yasg_response(
                _("系统设置"), examples={setting[0]: setting[2] for setting in DEFAULT_SETTINGS}
            )
        },
        tags=tags,
    )
    @action(detail=False, methods=["get"])
    def simple(self, request, *args, **kwargs):
        """获取系统配置表 -> {"key": "value"}"""

        return Response({q.key: q.value for q in self.queryset})

    @common_swagger_auto_schema(
        operation_summary=_("查询相关系统的地址"),
        tags=tags,
    )
    @action(detail=False, methods=["get"])
    def related_system_urls(self, request):
        return Response({"BK_CMDB_URL": env.BK_CMDB_URL})
