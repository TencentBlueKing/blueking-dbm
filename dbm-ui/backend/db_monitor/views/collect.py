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

from backend import env
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import SystemViewSet
from backend.components import BKMonitorV3Api
from backend.db_monitor.models import CollectInstance
from backend.db_monitor.serializers import (
    ImportCollectPluginSerializer,
    ListCollectPluginSerializer,
    SyncCollectStrategySerializer,
)

SWAGGER_TAG = _("采集策略")


class CollectViewSet(SystemViewSet):
    """采集策略相关接口"""

    queryset = CollectInstance.objects.all()
    default_permission_class = []
    action_permission_map = {
        ("sync_strategy", "plugin_list", "plugin_import"): [],
    }

    @common_swagger_auto_schema(
        operation_summary=_("加载/同步采集策略到蓝鲸监控"),
        request_body=SyncCollectStrategySerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        url_path="sync/strategy",
        serializer_class=SyncCollectStrategySerializer,
    )
    def sync_strategy(self, request, *args, **kwargs):
        """加载/同步采集策略到蓝鲸监控"""
        params = self.validated_data
        kwargs_ = {}
        db_type = params.get("db_type") or None
        if db_type:
            kwargs_["db_type"] = db_type
        if params.get("force"):
            kwargs_["force"] = True
        bk_biz_id = params.get("bk_biz_id")
        if bk_biz_id:
            kwargs_["bk_biz_id"] = bk_biz_id

        CollectInstance.sync_collect_strategy(**kwargs_)
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("获取采集插件列表"),
        query_serializer=ListCollectPluginSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["GET"], serializer_class=ListCollectPluginSerializer)
    def plugin_list(self, request, *args, **kwargs):
        """获取蓝鲸监控采集插件列表"""
        data = self.params_validate(self.get_serializer_class())
        bk_biz_id = data.get("bk_biz_id") or env.DBA_APP_BK_BIZ_ID
        resp = BKMonitorV3Api.collector_plugin_list({"bk_biz_id": bk_biz_id})
        return Response(resp)

    @common_swagger_auto_schema(
        operation_summary=_("导入采集插件"),
        request_body=ImportCollectPluginSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=ImportCollectPluginSerializer)
    def plugin_import(self, request, *args, **kwargs):
        """导入采集插件到蓝鲸监控(无前端导入方式)"""
        data = self.params_validate(self.get_serializer_class())
        bk_biz_id = data.get("bk_biz_id") or env.DBA_APP_BK_BIZ_ID
        plugin_file = data.get("file")
        params = {
            "bk_biz_id": bk_biz_id,
            "file_data": plugin_file,
        }
        resp = BKMonitorV3Api.plugin_import_without_frontend(params, use_admin=True)
        return Response(resp)
