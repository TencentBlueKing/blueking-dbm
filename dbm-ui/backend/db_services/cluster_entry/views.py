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
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster
from backend.db_services.cluster_entry.serializers import ModifyClusterEntrySerializer, RetrieveClusterEntrySLZ
from backend.db_services.dbbase.resources.query import ListRetrieveResource
from backend.flow.utils.dns_manage import DnsManage
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission, GlobalManageIAMPermission

logger = logging.getLogger("root")
SWAGGER_TAG = [_("集群访问入口")]


class ClusterEntryViewSet(viewsets.SystemViewSet):
    permission_classes = [GlobalManageIAMPermission]

    def _get_custom_permissions(self):
        if self.action == "get_cluster_entries":
            return [DBManageIAMPermission()]

        return [GlobalManageIAMPermission()]

    @common_swagger_auto_schema(operation_summary=_("修改集群访问入口"), tags=[SWAGGER_TAG])
    @action(methods=["POST"], detail=False, serializer_class=ModifyClusterEntrySerializer)
    def refresh_cluster_domain(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        cluster = Cluster.objects.get(id=data["cluster_id"])
        for detail in data["cluster_entry_details"]:
            if detail["cluster_entry_type"] == ClusterEntryType.DNS:
                DnsManage(cluster.bk_biz_id, cluster.bk_cloud_id).refresh_cluster_domain(
                    detail["domain_name"], detail["target_instances"]
                )
        return Response({})

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

        cluster = Cluster.objects.get(id=self.validated_data["cluster_id"])
        cluster_entries = ListRetrieveResource.query_cluster_entry_details(
            {
                "id": cluster.id,
                "bk_cloud_id": cluster.bk_cloud_id,
                "bk_biz_id": cluster.bk_biz_id,
            },
            cluster_entry_type=self.validated_data["entry_type"],
        )

        return Response(cluster_entries)
