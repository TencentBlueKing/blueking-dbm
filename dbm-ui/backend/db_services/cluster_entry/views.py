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
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.cluster_entry.serializers import ModifyClusterEntrySerializer, RetrieveClusterEntrySLZ
from backend.db_services.dbbase.resources.query import ListRetrieveResource
from backend.flow.utils.dns_manage import DnsManage
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import (
    BizDBTypeResourceActionPermission,
    DBManagePermission,
    ResourceActionPermission,
    get_request_key_id,
)

logger = logging.getLogger("root")
SWAGGER_TAG = [_("集群访问入口")]


class ClusterEntryViewSet(viewsets.SystemViewSet):
    @staticmethod
    def instance_biz_getter(request, view):
        cluster_id = get_request_key_id(request, key="cluster_id")
        bk_biz_id = Cluster.objects.get(cluster_id=cluster_id).bk_biz_id
        return [bk_biz_id]

    @staticmethod
    def instance_dbtype_getter(request, view):
        cluster_id = get_request_key_id(request, key="cluster_id")
        dbtype = ClusterType.cluster_type_to_db_type(Cluster.objects.get(cluster_id=cluster_id).cluster_type)
        return [dbtype]

    def get_action_permission_map(self) -> dict:
        return {
            ("get_cluster_entries",): [DBManagePermission()],
            ("refresh_cluster_domain",): [
                BizDBTypeResourceActionPermission(
                    [ActionEnum.ACCESS_ENTRY_EDIT],
                    instance_biz_getter=self.instance_biz_getter,
                    instance_dbtype_getter=self.instance_dbtype_getter,
                )
            ],
        }

    def get_default_permission_class(self) -> list:
        return [ResourceActionPermission([ActionEnum.GLOBAL_MANAGE])]

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

        cluster_entry_type = self.validated_data.get("entry_type")
        extra = {"cluster_entry_type": cluster_entry_type} if cluster_entry_type else {}
        cluster_entries = ListRetrieveResource.query_cluster_entry_details(
            {
                "id": cluster.id,
                "bk_cloud_id": cluster.bk_cloud_id,
                "bk_biz_id": cluster.bk_biz_id,
            },
            **extra
        )

        return Response(cluster_entries)
