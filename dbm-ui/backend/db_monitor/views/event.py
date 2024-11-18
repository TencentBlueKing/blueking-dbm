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
from backend.configuration.models import DBAdministrator
from backend.db_monitor import serializers
from backend.db_monitor.constants import SWAGGER_TAG
from backend.iam_app.handlers.drf_perm.base import DBManagePermission


class AlertView(SystemViewSet):
    def _get_custom_permissions(self):
        return [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("告警事件列表"),
        request_body=serializers.ListAlertSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=serializers.ListAlertSerializer)
    def search(self, request):
        params = self.validated_data
        params.update(
            {
                "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID],
                "start_time": self.validated_data.get("start_time").timestamp(),
                "end_time": self.validated_data.get("end_time").timestamp(),
            }
        )
        filter_key_map = {
            "bk_biz_id": "tags.appid",
            "cluster_domain": "tags.cluster_domain",
            "severity": "severity",
            "stage": "stage",
            "status": "status",
        }
        conditions = []
        for key, target_key in filter_key_map.items():
            if key in params:
                conditions.append(f"{target_key}: {params[key]}")

        # 查询用户管理的告警事件，查出用户管理的业务，添加到查询条件中
        self_manage = params.pop("self_manage")
        self_assist = params.pop("self_assist")
        dbas = DBAdministrator.objects.filter(users__contains=request.user.username)
        biz_cluster_type_conditions = []
        if self_manage:
            # 主负责的业务（第一个 DBA）
            biz_cluster_type_conditions = (
                # TODO 目前策略的维度没有 db_type或 cluster_type，需要给策略都加上
                # f"tags.appid : {dba.bk_biz_id} AND tags.db_type : {dba.db_type} "
                f"tags.appid : {dba.bk_biz_id}"
                for dba in dbas
                if dba.users[0] == request.user.username
            )
        elif self_assist:
            # 协助的业务（非第一个 DBA）
            biz_cluster_type_conditions = (
                # f"tags.appid : {dba.bk_biz_id} AND tags.db_type : {dba.db_type} "
                f"tags.appid : {dba.bk_biz_id}"
                for dba in dbas
                if dba.users[0] != request.user.username
            )
        biz_cluster_type_query_string = " OR ".join(biz_cluster_type_conditions)
        if biz_cluster_type_query_string:
            conditions.append(f"({biz_cluster_type_query_string})")

        params["query_string"] = " AND ".join(conditions)

        data = BKMonitorV3Api.search_alert(params)
        return Response(data)
