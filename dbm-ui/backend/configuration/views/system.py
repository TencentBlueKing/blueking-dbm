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

from backend import env
from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import domains
from backend.configuration.constants import DISK_CLASSES, SystemSettingsEnum
from backend.configuration.models.system import BizSettings, SystemSettings
from backend.configuration.serializers import (
    BizSettingsSerializer,
    ListBizSettingsResponseSerializer,
    ListBizSettingsSerializer,
    UpdateBizSettingsSerializer,
)
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission, RejectPermission

tags = [_("系统设置")]


class SystemSettingsViewSet(viewsets.SystemViewSet):
    """系统设置视图"""

    def _get_custom_permissions(self):
        # 非超级用户拒绝访问敏感信息
        if self.action == self.sensitive_environ.__name__ and not self.request.user.is_superuser:
            return [RejectPermission()]

        return []

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
        """按需提供非敏感环境变量"""
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

    @common_swagger_auto_schema(operation_summary=_("查询环境变量"), tags=tags)
    @action(detail=False, methods=["get"])
    def sensitive_environ(self, request):
        """按需提供敏感环境变量"""
        dbm_report = SystemSettings.get_setting_value(key=SystemSettingsEnum.BKM_DBM_REPORT.value)
        return Response(
            {
                "MONITOR_METRIC_DATA_ID": dbm_report["metric"]["data_id"],
                "MONITOR_EVENT_DATA_ID": dbm_report["event"]["data_id"],
                "MONITOR_METRIC_ACCESS_TOKEN": dbm_report["metric"]["token"],
                "MONITOR_EVENT_ACCESS_TOKEN": dbm_report["event"]["token"],
                "MONITOR_SERVICE": dbm_report["proxy"],
            }
        )


class BizSettingsViewSet(viewsets.AuditedModelViewSet):
    """业务设置视图"""

    serializer_class = BizSettingsSerializer
    queryset = BizSettings.objects.all()

    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("业务设置列表"),
        responses={status.HTTP_200_OK: BizSettingsSerializer(_("业务设置"), many=True)},
        tags=tags,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("业务设置列表键值映射表"),
        query_serializer=ListBizSettingsSerializer(),
        responses={status.HTTP_200_OK: ListBizSettingsResponseSerializer()},
        tags=tags,
    )
    @action(detail=False, methods=["GET"], serializer_class=ListBizSettingsSerializer)
    def simple(self, request, *args, **kwargs):
        filter_field = self.params_validate(self.get_serializer_class())
        return Response({q.key: q.value for q in self.queryset.filter(**filter_field)})

    @common_swagger_auto_schema(
        operation_summary=_("更新业务设置列表键值"),
        request_body=UpdateBizSettingsSerializer(),
        tags=tags,
    )
    @action(detail=False, methods=["POST"], serializer_class=UpdateBizSettingsSerializer)
    def update_settings(self, request, *args, **kwargs):
        setting_data = self.params_validate(self.get_serializer_class())
        BizSettings.insert_setting_value(**setting_data, user=request.user.username)
        return Response()
