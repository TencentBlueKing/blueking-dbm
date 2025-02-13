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
from backend.db_monitor import serializers
from backend.db_monitor.constants import SWAGGER_TAG
from backend.db_monitor.utils import deformat_shield_description, format_shield_description
from backend.iam_app.handlers.drf_perm.base import DBManagePermission, RejectPermission


class AlarmShieldView(SystemViewSet):
    def _get_custom_permissions(self):
        if self.action == "list":
            return [DBManagePermission()]
        elif self.action == "create":
            return [DBManagePermission()]
        elif self.action in ["disable", "update"]:
            return [DBManagePermission()]
        return [RejectPermission()]

    def get_serializer_class(self):
        action_slz_map = {
            "list": serializers.ListAlarmShieldSerializer,
            "create": serializers.CreateAlarmShieldSerializer,
            "update": serializers.UpdateAlarmShieldSerializer,
            "disable": serializers.DisableAlarmShieldSerializer,
        }
        return action_slz_map.get(self.action)

    @common_swagger_auto_schema(
        operation_summary=_("告警屏蔽列表"),
        query_serializer=serializers.ListAlarmShieldSerializer(),
        tags=[SWAGGER_TAG],
    )
    def list(self, request):
        params = self.validated_data
        page_size = int(request.query_params.get("limit", 10))
        page = int(int(request.query_params.get("offset", 0)) / page_size) + 1
        if params.get("category"):
            params["categories"] = [params["category"]]
        conditions = params.get("conditions", [])
        conditions.append({"key": "query", "value": format_shield_description(params["bk_biz_id"])})
        params.update(
            {
                "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID],
                "page": page,
                "page_size": page_size,
                "conditions": conditions,
            }
        )
        data = BKMonitorV3Api.list_shield(params)
        for index, shield in enumerate(data["shield_list"]):
            data["shield_list"][index]["description"] = deformat_shield_description(
                params["bk_biz_id"], shield["description"]
            )
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("告警屏蔽详情"),
        tags=[SWAGGER_TAG],
    )
    def retrieve(self, request, pk):
        return Response(BKMonitorV3Api.get_shield({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "id": pk}))

    @common_swagger_auto_schema(
        operation_summary=_("新增告警屏蔽"),
        request_body=serializers.CreateAlarmShieldSerializer(),
        tags=[SWAGGER_TAG],
    )
    def create(self, request):
        data = self.validated_data
        data.update(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "description": format_shield_description(data["bk_biz_id"], description=data["description"]),
            }
        )
        return Response(BKMonitorV3Api.add_shield(data))

    @common_swagger_auto_schema(
        operation_summary=_("解除告警屏蔽"),
        request_body=serializers.DisableAlarmShieldSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=True, methods=["POST"])
    def disable(self, request, pk):
        return Response(BKMonitorV3Api.disable_shield({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "id": pk}))

    @common_swagger_auto_schema(
        operation_summary=_("编辑告警屏蔽"),
        request_body=serializers.UpdateAlarmShieldSerializer(),
        tags=[SWAGGER_TAG],
    )
    def update(self, request, pk):
        shield = BKMonitorV3Api.get_shield({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "id": pk})
        data = self.validated_data
        data.update(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "id": pk,
                "description": format_shield_description(shield["bk_biz_id"], description=data["description"]),
            }
        )
        return Response(BKMonitorV3Api.edit_shield(data))
