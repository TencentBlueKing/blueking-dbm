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
from typing import Dict, List

from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.models import Cluster
from backend.db_meta.models.sqlserver_dts import SqlserverDtsInfo
from backend.db_services.sqlserver.data_migrate.handlers import SQLServerDataMigrateHandler
from backend.db_services.sqlserver.data_migrate.serializers import (
    ForceFailedMigrateSerializer,
    ManualTerminateSyncResponseSerializer,
    ManualTerminateSyncSerializer,
    QueryMigrateRecordsResponseSerializer,
    QueryMigrateRecordsSerializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

SWAGGER_TAG = "db_services/sqlserver/migrate"


class SQLServerDataMigrateViewSet(viewsets.SystemViewSet):
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("手动断开同步"),
        request_body=ManualTerminateSyncSerializer(),
        responses={status.HTTP_200_OK: ManualTerminateSyncResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ManualTerminateSyncSerializer)
    def manual_terminate_sync(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        ticket = SQLServerDataMigrateHandler.manual_terminate_sync(ticket_id=data["ticket_id"], dts_id=data["dts_id"])
        return Response({"ticket_id": ticket.id})

    @common_swagger_auto_schema(
        operation_summary=_("强制终止"),
        request_body=ForceFailedMigrateSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ForceFailedMigrateSerializer)
    def force_failed_migrate(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        SQLServerDataMigrateHandler.force_failed_migrate(dts_id=data["dts_id"])
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("获取迁移记录"),
        query_serializer=QueryMigrateRecordsSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: QueryMigrateRecordsResponseSerializer()},
    )
    @action(methods=["GET"], detail=False, serializer_class=QueryMigrateRecordsSerializer)
    def query_migrate_records(self, request, bk_biz_id):
        data = self.params_validate(self.get_serializer_class())
        # (不分页)获取全量的迁移记录
        migrate_records = SqlserverDtsInfo.objects.filter(bk_biz_id=bk_biz_id).order_by("-create_at").values()

        # 收集所有的集群 ID，避免重复
        cluster_ids = set()
        for record in migrate_records:
            cluster_ids.add(record["source_cluster_id"])
            cluster_ids.update(record["target_cluster_ids"])

        # 获取所有涉及的集群，并建立 ID 到域名的映射
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        cluster_id_to_domain = {cluster.id: cluster.immute_domain for cluster in clusters}

        # 过滤符合条件的记录并添加域名信息
        filtered_migrate_records: List[Dict] = []
        cluster_name = data["cluster_name"]
        for record in migrate_records:
            source_domain = cluster_id_to_domain.get(record["source_cluster_id"], "")
            target_domains = [cluster_id_to_domain.get(target_id, "") for target_id in record["target_cluster_ids"]]

            # 过滤不符合条件的记录
            if cluster_name in source_domain or cluster_name in target_domains:
                filtered_migrate_records.append(
                    {**record, "source_cluster_domain": source_domain, "target_cluster_domain": target_domains}
                )

        return Response(filtered_migrate_records)
