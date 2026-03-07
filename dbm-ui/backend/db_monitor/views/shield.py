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
from backend.db_monitor.utils import deformat_shield_description, format_shield_description, parse_shield_description_biz
from backend.iam_app.dataclass import ActionEnum, ResourceEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.monitor import AlertShieldPermission
from backend.iam_app.handlers.permission import Permission


class AlarmShieldView(SystemViewSet):

    action_permission_map = {
        ("list",): [DBManagePermission()],
        (
            "disable",
            "update",
            "create",
            "retrieve",
        ): [AlertShieldPermission()],
    }

    def get_serializer_class(self):
        action_slz_map = {
            "list": serializers.ListAlarmShieldSerializer,
            "create": serializers.CreateAlarmShieldSerializer,
            "update": serializers.UpdateAlarmShieldSerializer,
            "disable": serializers.DisableAlarmShieldSerializer,
            "retrieve": serializers.serializers.Serializer,
        }
        return action_slz_map.get(self.action)

    @common_swagger_auto_schema(
        operation_summary=_("告警屏蔽列表"),
        query_serializer=serializers.ListAlarmShieldSerializer(),
        tags=[SWAGGER_TAG],
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["bk_biz_id"],
        actions=[ActionEnum.ALERT_SHIELD_CREATE, ActionEnum.ALERT_SHIELD_MANAGE],
        resource_meta=ResourceEnum.BUSINESS,
    )
    def list(self, request):
        params = self.validated_data
        bk_biz_id = params["bk_biz_id"]
        page_size = int(request.query_params.get("limit", 10))
        page = int(int(request.query_params.get("offset", 0)) / page_size) + 1
        if params.get("category"):
            params["categories"] = [params["category"]]
        base_conditions = params.get("conditions", [])

        # 查询1：DBM 通过接口创建的屏蔽（description 含 [dbm:appid=xxx] 前缀）
        dbm_conditions = list(base_conditions)
        dbm_conditions.append({"key": "description", "value": format_shield_description(bk_biz_id)})
        dbm_params = dict(params)
        dbm_params.update(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID],
                "page": 1,
                "page_size": 500,
                "conditions": dbm_conditions,
            }
        )
        dbm_data = BKMonitorV3Api.list_shield(dbm_params)

        # 查询2：手机端直接在目标业务下创建的屏蔽（bk_biz_ids 包含目标业务 appid）
        app_params = dict(params)
        app_params.update(
            {
                "bk_biz_id": bk_biz_id,
                "bk_biz_ids": [bk_biz_id],
                "page": 1,
                "page_size": 500,
                "conditions": list(base_conditions),
            }
        )
        app_data = BKMonitorV3Api.list_shield(app_params)

        # 合并去重（以 shield id 为唯一键），DBM 创建的优先（description 会被格式化）
        seen_ids = set()
        merged_shields = []

        for shield in dbm_data.get("shield_list", []):
            if shield["id"] not in seen_ids:
                seen_ids.add(shield["id"])
                shield["description"] = deformat_shield_description(bk_biz_id, shield["description"])
                merged_shields.append(shield)

        for shield in app_data.get("shield_list", []):
            if shield["id"] not in seen_ids:
                # 手机端创建的屏蔽，description 无 DBM 前缀，直接保留
                seen_ids.add(shield["id"])
                merged_shields.append(shield)

        # 对合并结果做分页
        total = len(merged_shields)
        start = (page - 1) * page_size
        end = start + page_size
        paged_shields = merged_shields[start:end]

        return Response({"count": total, "shield_list": paged_shields})

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
