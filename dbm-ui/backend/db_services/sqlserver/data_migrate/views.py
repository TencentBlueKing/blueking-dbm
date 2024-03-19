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
import itertools
from typing import Dict, List

from django.forms.models import model_to_dict
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
    def _get_custom_permissions(self):
        return [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("手动断开同步"),
        request_body=ManualTerminateSyncSerializer(),
        responses={status.HTTP_200_OK: ManualTerminateSyncResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ManualTerminateSyncSerializer)
    def manual_terminate_sync(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        ticket = SQLServerDataMigrateHandler.manual_terminate_sync(ticket_id=data["ticket_id"])
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
        migrate_records = [model_to_dict(dts) for dts in SqlserverDtsInfo.objects.filter(bk_biz_id=bk_biz_id)]
        cluster_tuple_ids = [[record["source_cluster_id"], record["target_cluster_id"]] for record in migrate_records]
        clusters = Cluster.objects.filter(id__in=list(set(itertools.chain(*cluster_tuple_ids))))
        cluster_id__cluster_domain = {cluster.id: cluster.immute_domain for cluster in clusters}
        # 完善迁移记录信息
        filter_migrate_records: List[Dict] = []
        for record in migrate_records:
            source_domain = cluster_id__cluster_domain[record["source_cluster_id"]]
            target_domain = cluster_id__cluster_domain[record["target_cluster_id"]]
            # 过滤集群域名
            if data["cluster_name"] not in source_domain and data["cluster_name"] not in target_domain:
                continue
            filter_migrate_records.append(
                {**record, "source_cluster_domain": source_domain, "target_cluster_domain": target_domain}
            )

        return Response(filter_migrate_records)
