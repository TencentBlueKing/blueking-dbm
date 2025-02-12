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
from datetime import datetime, timedelta
from typing import Any, Dict, List

from django.utils import timezone
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.comm import SystemTagEnum
from backend.db_meta.models import Cluster
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.db_services.mysql.fixpoint_rollback.serializers import (
    BackupLocalLogMySQLResponseSerializer,
    BackupLogMySQLResponseSerializer,
    BackupLogRollbackTimeMySQLResponseSerializer,
    BackupLogRollbackTimeSerializer,
    BackupLogRollbackTimeTendbResponseSerializer,
    BackupLogSerializer,
    BackupLogTendbResponseSerializer,
    QueryFixpointLogResponseSerializer,
    QueryFixpointLogSerializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.ticket.constants import TicketType
from backend.ticket.models import ClusterOperateRecord
from backend.utils.time import str2datetime

SWAGGER_TAG = "db_services/mysql/fixpoint_rollback"


class FixPointRollbackViewSet(viewsets.SystemViewSet):
    action_permission_map = {}
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("通过日志平台获取集群备份记录"),
        query_serializer=BackupLogSerializer(),
        responses={
            status.HTTP_200_OK: BackupLogTendbResponseSerializer(),
            status.HTTP_202_ACCEPTED: BackupLogMySQLResponseSerializer(),
        },
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=BackupLogSerializer)
    def query_backup_log_from_bklog(self, requests, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=validated_data["days"])
        handler = FixPointRollbackHandler(validated_data["cluster_id"], check_full_backup=True)
        logs = handler.query_backup_log_from_bklog(start_time, end_time)
        logs.sort(key=lambda x: x["backup_time"], reverse=True)
        return Response(logs)

    @common_swagger_auto_schema(
        operation_summary=_("查询集群的本地备份记录"),
        query_serializer=BackupLogSerializer(),
        responses={status.HTTP_200_OK: BackupLocalLogMySQLResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=BackupLogSerializer)
    def query_backup_log_from_local(self, requests, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        logs = FixPointRollbackHandler(validated_data["cluster_id"]).query_backup_log_from_local()
        return Response(logs)

    @common_swagger_auto_schema(
        operation_summary=_("查询小于回档时间点最近的备份记录"),
        query_serializer=BackupLogRollbackTimeSerializer(),
        responses={
            status.HTTP_200_OK: BackupLogRollbackTimeTendbResponseSerializer(),
            status.HTTP_202_ACCEPTED: BackupLogRollbackTimeMySQLResponseSerializer(),
        },
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=BackupLogRollbackTimeSerializer)
    def query_latest_backup_log(self, requests, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        handler = FixPointRollbackHandler(validated_data["cluster_id"], check_full_backup=True)
        return Response(
            handler.query_latest_backup_log(
                rollback_time=str2datetime(validated_data["rollback_time"]),
                backup_source=validated_data.get("backup_source"),
            )
        )

    @common_swagger_auto_schema(
        operation_summary=_("获取定点构造记录"),
        query_serializer=QueryFixpointLogSerializer(),
        responses={status.HTTP_200_OK: QueryFixpointLogResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=QueryFixpointLogSerializer, pagination_class=None)
    def query_fixpoint_log(self, requests, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        limit, offset = validated_data["limit"], validated_data["offset"]

        # 查询目前定点回档临时集群
        tmp_clusters = Cluster.objects.filter(cluster_type=ClusterType.TenDBCluster, tag__name=SystemTagEnum.TEMPORARY)
        tmp_clusters_count = tmp_clusters.count()
        # 查询定点回档记录
        temp_clusters = tmp_clusters[offset : limit + offset]
        temp_cluster_ids = [cluster.id for cluster in temp_clusters]
        records = ClusterOperateRecord.objects.select_related("ticket").filter(
            cluster_id__in=temp_cluster_ids, ticket__ticket_type=TicketType.TENDBCLUSTER_ROLLBACK_CLUSTER
        )
        # 填充定点回档实例记录
        fixpoint_logs: List[Dict[str, Any]] = []
        for record in records:
            ticket_data = record.ticket.details["infos"][0]
            clusters = record.ticket.details["clusters"]
            target_cluster = Cluster.objects.get(id=record.cluster_id)
            fixpoint_logs.append(
                {
                    "databases": ticket_data["databases"],
                    "databases_ignore": ticket_data["databases_ignore"],
                    "tables": ticket_data["tables"],
                    "tables_ignore": ticket_data["tables_ignore"],
                    "source_cluster": clusters[str(ticket_data["cluster_id"])],
                    "target_cluster": {
                        "cluster_id": record.cluster_id,
                        "nodes": ticket_data["rollback_host"],
                        "status": target_cluster.status,
                        "phase": target_cluster.phase,
                        "operations": ClusterOperateRecord.objects.get_cluster_operations(record.cluster_id),
                    },
                    "ticket_id": record.ticket.id,
                    "rollback_type": ticket_data["rollback_type"],
                    "rollback_time": ticket_data.get("rollback_time", ""),
                    "backupinfo": ticket_data.get("backupinfo", {}).get("backup_time", ""),
                }
            )

        return Response({"count": tmp_clusters_count, "results": fixpoint_logs})
