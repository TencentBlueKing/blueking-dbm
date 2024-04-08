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
from datetime import datetime

from django.utils.translation import ugettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.hadb.client import HADBApi
from backend.db_event.serializers import QueryDetailSerializer, QueryListSerializer
from backend.db_meta.models import AppCache, Cluster
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission, get_request_key_id
from backend.iam_app.handlers.permission import Permission

SWAGGER_TAG = _("DBHA事件")


class DBHAEventViewSet(viewsets.SystemViewSet):
    def get_action_permission_map(self):
        return {("cat",): []}

    def get_default_permission_class(self):
        return [ResourceActionPermission([ActionEnum.DBHA_SWITCH_EVENT_VIEW], ResourceEnum.BUSINESS, self.inst_getter)]

    @staticmethod
    def inst_getter(request, view):
        return [get_request_key_id(request, "app")]

    @common_swagger_auto_schema(
        operation_summary=_("DBHA切换事件列表"),
        query_serializer=QueryListSerializer,
        tags=[SWAGGER_TAG],
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["app"],
        actions=[ActionEnum.DBHA_SWITCH_EVENT_VIEW],
        resource_meta=ResourceEnum.BUSINESS,
    )
    @action(methods=["GET"], detail=False, serializer_class=QueryListSerializer, pagination_class=None)
    def ls(self, request):
        validated_data = self.params_validate(self.get_serializer_class())

        switch_start_time = validated_data.get("switch_start_time", None)
        if switch_start_time:
            validated_data["switch_start_time"] = switch_start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        switch_finished_time = validated_data.get("switch_finished_time", None)
        if switch_finished_time:
            validated_data["switch_finished_time"] = switch_finished_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        # dbha要求app为str
        if "app" in validated_data:
            validated_data["app"] = str(validated_data["app"])

        switch_queues = HADBApi.switch_queue(params={"name": "query_switch_queue", "query_args": validated_data})

        # fill bk_biz_name
        id_to_name = AppCache.id_to_name()
        cluster_domains = {switch["cluster"] for switch in switch_queues}
        clusters = {
            cluster["immute_domain"]: cluster
            for cluster in Cluster.objects.filter(immute_domain__in=cluster_domains).values(
                "immute_domain", "cluster_type", "id"
            )
        }
        # fill cluster
        for switch in switch_queues:
            switch["bk_biz_id"] = int(switch["app"])
            switch["bk_biz_name"] = id_to_name.get(switch["bk_biz_id"])
            switch.update(cluster_info=clusters.get(switch["cluster"], {}))

        return Response(switch_queues)

    @common_swagger_auto_schema(
        operation_summary=_("DBHA切换事件详情（日志）"),
        query_serializer=QueryDetailSerializer,
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=QueryDetailSerializer, pagination_class=None)
    def cat(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        logs = HADBApi.switch_logs(
            params={"name": "query_switch_log", "query_args": {"sw_id": validated_data["sw_id"]}},
            raw=False,
        )

        # 格式化时间戳
        switch_logs = []
        for log in logs:
            # "%Y-%m-%dT%H:%M:%S+08:00"
            log_time = datetime.strptime(log["datetime"][:-6], "%Y-%m-%dT%H:%M:%S")
            switch_logs.append(
                {
                    "timestamp": datetime.timestamp(log_time) * 1000,
                    "levelname": log.get("result"),
                    "message": f"[dbha]: {log['comment']}",
                }
            )

        return Response(switch_logs)
