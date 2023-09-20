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

from backend import env
from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DISK_CLASSES, SystemSettingsEnum
from backend.configuration.models import SystemSettings

tags = [_("系统设置")]


class SystemSettingsViewSet(viewsets.SystemViewSet):
    """系统设置视图"""

    @common_swagger_auto_schema(
        operation_summary=_("查询磁盘类型"),
        tags=tags,
    )
    @action(methods=["GET"], detail=False)
    def disk_classes(self, request, *args, **kwargs):
        return Response(DISK_CLASSES)

    @common_swagger_auto_schema(
        operation_summary=_("查询机型类型"),
        tags=tags,
    )
    @action(methods=["GET"], detail=False)
    def device_classes(self, request, *args, **kwargs):
        return Response(SystemSettings.get_setting_value(SystemSettingsEnum.DEVICE_CLASSES.value, default=[]))

    @common_swagger_auto_schema(operation_summary=_("查询环境变量"), tags=tags)
    @action(detail=False, methods=["get"])
    def environ(self, request):
        """按需提供环境变量"""
        return Response(
            {
                "BK_DOMAIN": env.BK_DOMAIN,
                "BK_COMPONENT_API_URL": env.BK_COMPONENT_API_URL,
                "BK_CMDB_URL": env.BK_CMDB_URL,
                "BK_NODEMAN_URL": env.BK_NODEMAN_URL,
                "BK_SCR_URL": env.BK_SCR_URL,
                "BK_HELPER_URL": env.BK_HELPER_URL,
            }
        )
