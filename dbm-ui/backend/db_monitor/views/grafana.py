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

from backend.bk_dataview.grafana.constants import DEFAULT_ORG_ID, DEFAULT_ORG_NAME
from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_monitor.models import Dashboard
from backend.db_monitor.serializers import (
    DashboardUrlSerializer,
    GetBusinessDashboardSerializer,
    GetDashboardSerializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.cluster import ClusterDetailPermission

from .. import constants
from ..constants import DashboardType


class MonitorGrafanaViewSet(viewsets.SystemViewSet):

    action_permission_map = {
        ("get_dashboard",): [ClusterDetailPermission()],
        ("get_business_dashboard",): [DBManagePermission()],
    }

    @common_swagger_auto_schema(
        operation_summary=_("查询内嵌仪表盘地址"),
        query_serializer=GetDashboardSerializer,
        responses={status.HTTP_200_OK: DashboardUrlSerializer},
        tags=[constants.SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetDashboardSerializer, pagination_class=None)
    def get_dashboard(self, request):
        validated_data = self.params_validate(self.get_serializer_class())

        bk_biz_id = validated_data.get("bk_biz_id")
        cluster_id = validated_data.get("cluster_id")
        cluster_type = validated_data.get("cluster_type")

        # instance = StorageInstance.objects.filter(id=instance_id).last()

        dashes = Dashboard.objects.filter(
            org_id=DEFAULT_ORG_ID, org_name=DEFAULT_ORG_NAME, cluster_type=cluster_type, type=DashboardType.CLUSTER
        )
        if dashes.exists():
            dash_urls = [{"view": dash.view, "url": dash.get_url(bk_biz_id, cluster_id)} for dash in dashes]
            url = dash_urls[0]["url"]
        else:
            dash_urls, url = [], "#"

        return Response({"url": url, "urls": dash_urls})

    @common_swagger_auto_schema(
        operation_summary=_("查询业务仪表盘地址"),
        query_serializer=GetBusinessDashboardSerializer,
        responses={status.HTTP_200_OK: DashboardUrlSerializer},
        tags=[constants.SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetBusinessDashboardSerializer, pagination_class=None)
    def get_business_dashboard(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_data.get("bk_biz_id")
        dashes = Dashboard.objects.filter(
            org_id=DEFAULT_ORG_ID, org_name=DEFAULT_ORG_NAME, type=DashboardType.BUSINESS
        )

        if dashes.exists():
            dash_urls = [
                {"view": dash.view, "url": dash.get_business_url(bk_biz_id), "db_type": dash.db_type}
                for dash in dashes
            ]
            url = dash_urls[0]["url"]
        else:
            dash_urls, url = [], "#"

        return Response({"url": url, "urls": dash_urls})
