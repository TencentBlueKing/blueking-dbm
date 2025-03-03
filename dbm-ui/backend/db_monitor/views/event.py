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
from backend.iam_app.dataclass import ActionEnum, ResourceEnum
from backend.iam_app.handlers.drf_perm.monitor import ListAlertEventPermission
from backend.iam_app.handlers.permission import Permission


class AlertView(SystemViewSet):
    action_permission_map = {("search",): [ListAlertEventPermission()]}

    @common_swagger_auto_schema(
        operation_summary=_("告警事件列表"),
        request_body=serializers.ListAlertSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(detail=False, methods=["POST"], serializer_class=serializers.ListAlertSerializer)
    @Permission.decorator_permission_field(
        id_field=lambda alerts: int({a["key"]: a["value"] for a in alerts["tags"]}.get("appid", 0)),
        data_field=lambda d: d["alerts"],
        actions=[ActionEnum.ALERT_SHIELD_MANAGE, ActionEnum.ALERT_SHIELD_CREATE],
        resource_meta=ResourceEnum.BUSINESS,
    )
    def search(self, request):
        params = self.validated_data

        # 调整通用参数
        params.update(
            {
                "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID],
                "start_time": self.validated_data.get("start_time").timestamp(),
                "end_time": self.validated_data.get("end_time").timestamp(),
                "page": int(self.validated_data.get("offset") / self.validated_data.get("limit") + 1),
                "page_size": self.validated_data.get("limit"),
            }
        )

        # 通用查询条件拼接 querystring
        filter_key_map = {
            "bk_biz_id": "tags.appid",
            "cluster_domain": "tags.cluster_domain",
            "instance": "tags.instance",
            "ip": "ip",
            "alert_name": "alert_name",
            "description": "description",
            "severity": "severity",
            "stage": "stage",
            "status": "status",
        }
        multi_filter_fields = ["cluster_domain", "instance", "ip"]
        conditions = []
        for key, target_key in filter_key_map.items():
            if key in params:
                # 支持批量查询字段，都是以逗号分割
                if key in multi_filter_fields:
                    filter_conditions = " OR ".join([f'{target_key}: "{val}"' for val in params[key].split(",")])
                    conditions.append(f"({filter_conditions})")
                else:
                    conditions.append(f'{target_key}: "{params[key]}"')
                del params[key]

        # 查询用户管理的告警事件，查出用户管理的业务，添加到查询条件中
        self_manage = params.pop("self_manage")
        self_assist = params.pop("self_assist")
        dbas = DBAdministrator.objects.filter(users__contains=request.user.username)
        biz_cluster_type_conditions = []
        if self_manage:
            # 主负责的业务（第一个 DBA）
            biz_cluster_type_conditions = (
                f'tags.appid : "{dba.bk_biz_id}"' for dba in dbas if dba.users[0] == request.user.username
            )
        elif self_assist:
            # 协助的业务（非第一个 DBA）
            biz_cluster_type_conditions = (
                f'tags.appid : "{dba.bk_biz_id}"' for dba in dbas if dba.users[0] != request.user.username
            )
        biz_cluster_type_query_string = " OR ".join(set(biz_cluster_type_conditions))
        if biz_cluster_type_query_string:
            conditions.append(f"({biz_cluster_type_query_string})")

        # 如果过滤待我负责/协助，但自身不负责任何业务，则直接返回空
        if (self_manage or self_assist) and not biz_cluster_type_query_string:
            return Response({"alerts": [], "total": 0, "overview": {}, "aggs": []})

        # 拼接集群类型查询条件
        cluster_type_conditions = []
        for db_type in params.pop("db_types", []):
            cluster_type_conditions.append(f'labels : "DBM_{db_type.upper()}"')

        if cluster_type_conditions:
            conditions.append(f'({" OR ".join(cluster_type_conditions)})')

        params["query_string"] = " AND ".join(conditions)

        data = BKMonitorV3Api.search_alert(params)
        # 对于维度不包含appid的，暂时标记，无法做到鉴权和屏蔽
        for alert in data["alerts"]:
            tags = [tag["key"] for tag in alert["tags"]]
            alert.update(dbm_event=("appid" in tags))

        return Response(data)
