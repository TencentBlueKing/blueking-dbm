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

from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import BKMonitorV3Api
from backend.db_services.plugin.constants import SWAGGER_TAG
from backend.db_services.plugin.monitor.serializers import MonitorImageRenderSerializer, MonitorImageResultSerializer
from backend.iam_app.handlers.drf_perm.cluster import ClusterDashboardPermission


class MonitorPluginViewSet(viewsets.SystemViewSet):
    action_permission_map = {
        ("start_render_image_task",): [ClusterDashboardPermission()],
        ("get_render_image_task_result",): [],
    }

    @common_swagger_auto_schema(
        operation_summary=_("启动渲染图片任务"),
        request_body=MonitorImageRenderSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=MonitorImageRenderSerializer)
    def start_render_image_task(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        resp = BKMonitorV3Api.start_render_image_task(params=data)
        return Response(resp)

    @common_swagger_auto_schema(
        operation_summary=_("获取渲染图片任务结果"),
        query_serializer=MonitorImageResultSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=MonitorImageResultSerializer)
    def get_render_image_result(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        resp = BKMonitorV3Api.get_render_image_result(params=data)
        return Response(resp)
