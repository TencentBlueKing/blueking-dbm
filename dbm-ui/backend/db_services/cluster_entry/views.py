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
import logging

from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.cluster_entry.handlers import ClusterEntryHandler
from backend.db_services.cluster_entry.serializers import ModifyClusterEntrySerializer, RetrieveClusterEntrySLZ
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission, GlobalManageIAMPermission

logger = logging.getLogger("root")
SWAGGER_TAG = [_("集群访问入口")]


class ClusterEntryViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        if self.action == "get_cluster_entries":
            return [DBManageIAMPermission()]
        return [GlobalManageIAMPermission()]

    @common_swagger_auto_schema(operation_summary=_("修改集群访问入口"), tags=[SWAGGER_TAG])
    @action(methods=["POST"], detail=False, serializer_class=ModifyClusterEntrySerializer)
    def refresh_cluster_domain(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        ClusterEntryHandler(cluster_id=data["cluster_id"]).refresh_cluster_domain(
            cluster_entry_details=data["cluster_entry_details"]
        )
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("获取集群入口列表"),
        query_serializer=RetrieveClusterEntrySLZ(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="get_cluster_entries",
        serializer_class=RetrieveClusterEntrySLZ,
        pagination_class=None,
    )
    def get_cluster_entries(self, request, *args, **kwargs):
        """获取集群入口列表"""
        data = self.params_validate(self.get_serializer_class())
        cluster_entries = ClusterEntryHandler(cluster_id=data["cluster_id"]).get_cluster_entries(
            data["bk_biz_id"], data.get("entry_type")
        )
        return Response(cluster_entries)
