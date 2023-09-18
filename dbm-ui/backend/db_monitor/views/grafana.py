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
import urllib

from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend import env
from backend.bk_dataview.grafana.views import DEFAULT_ORG_ID, DEFAULT_ORG_NAME
from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.models import AppCache, Cluster, StorageInstance
from backend.db_monitor.models import Dashboard
from backend.db_monitor.serializers import DashboardUrlSerializer, GetDashboardSerializer
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission

SWAGGER_TAG = _("监控告警管理")


class MonitorGrafanaViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        if self.action == "get_dashboard":
            bk_biz_id = self.request.query_params["bk_biz_id"]
            return [DBManageIAMPermission(bk_biz_id)]

        return super()._get_custom_permissions()

    @common_swagger_auto_schema(
        operation_summary=_("查询内嵌仪表盘地址"),
        query_serializer=GetDashboardSerializer,
        responses={status.HTTP_200_OK: DashboardUrlSerializer},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetDashboardSerializer, pagination_class=None)
    def get_dashboard(self, request):
        validated_data = self.params_validate(self.get_serializer_class())

        cluster_id = validated_data.get("cluster_id")
        instance_id = validated_data.get("instance_id")
        cluster_type = validated_data.get("cluster_type")
        bk_biz_id = validated_data.get("bk_biz_id")

        cluster = Cluster.objects.filter(id=cluster_id).last()
        instance = StorageInstance.objects.filter(id=instance_id).last()

        try:
            dash = Dashboard.objects.get(org_id=DEFAULT_ORG_ID, org_name=DEFAULT_ORG_NAME, cluster_type=cluster_type)
            params = {
                "orgId": DEFAULT_ORG_ID,
                "orgName": DEFAULT_ORG_NAME,
                "var-cluster_domain": getattr(cluster, "immute_domain", None),
                "var-cluster_name": getattr(cluster, "name", None),
                "var-instance": getattr(instance, "ip_port", None),
                "var-host": getattr(getattr(instance, "machine", None), "ip", None),
                "var-app_id": bk_biz_id,
                "var-app": AppCache.get_app_attr(bk_biz_id, default=bk_biz_id),
                "kiosk": 1,
            }

            url = env.BK_SAAS_HOST + f"{dash.url}?" + urllib.parse.urlencode(params)
        except Dashboard.DoesNotExist:
            url = "#"

        return Response({"url": url})
