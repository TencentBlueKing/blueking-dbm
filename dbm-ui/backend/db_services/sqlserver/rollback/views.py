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

from django.utils import timezone
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.sqlserver.rollback.handlers import SQLServerRollbackHandler
from backend.db_services.sqlserver.rollback.serializers import (
    QueryBackupLogsResponseSerializer,
    QueryBackupLogsSerializer,
    QueryDbsByBackupLogResponseSerializer,
    QueryDbsByBackupLogSerializer,
    QueryLatestBackupLogResponseSerializer,
    QueryLatestBackupLogSerializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.utils.time import str2datetime

SWAGGER_TAG = "db_services/sqlserver/rollback"


class SQLServerRollbackViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        return [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("查询集群备份记录"),
        request_body=QueryBackupLogsSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: QueryBackupLogsResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryBackupLogsSerializer)
    def query_backup_logs(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=data["days"])
        cluster_id = data["cluster_id"]
        return Response(SQLServerRollbackHandler(cluster_id).query_backup_logs(start_time, end_time))

    @common_swagger_auto_schema(
        operation_summary=_("根据回档时间集群最近备份记录"),
        request_body=QueryLatestBackupLogSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: QueryLatestBackupLogResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryLatestBackupLogSerializer)
    def query_latest_backup_log(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        cluster_id = data.pop("cluster_id")
        return Response(
            SQLServerRollbackHandler(cluster_id).query_latest_backup_log(
                rollback_time=str2datetime(data["rollback_time"])
            )
        )

    @common_swagger_auto_schema(
        operation_summary=_("根据备份记录和库匹配模式查询操作库"),
        request_body=QueryDbsByBackupLogSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: QueryDbsByBackupLogResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryDbsByBackupLogSerializer)
    def query_dbs_by_backup_log(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        cluster_id = data.pop("cluster_id")
        return Response(SQLServerRollbackHandler(cluster_id).query_dbs_by_backup_log(**data))
