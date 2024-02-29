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
from backend.db_services.mongodb.restore.constants import BACKUP_LOG_RANGE_DAYS
from backend.db_services.mongodb.restore.handlers import MongoDBRestoreHandler
from backend.db_services.mongodb.restore.serializers import (
    QueryBackupLogResponseSerializer,
    QueryBackupLogSerializer,
    QueryRestoreRecordResponseSerializer,
    QueryRestoreRecordSerializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

SWAGGER_TAG = "db_services/mongodb/restore"


class MongoDBRestoreViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        return [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("获取集群单据备份记录"),
        query_serializer=QueryBackupLogSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryBackupLogSerializer)
    def query_ticket_backup_log(self, requests, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=BACKUP_LOG_RANGE_DAYS)
        backup_logs = MongoDBRestoreHandler.query_ticket_backup_log(**data, start_time=start_time, end_time=end_time)
        return Response(backup_logs)

    @common_swagger_auto_schema(
        operation_summary=_("获取集群备份记录"),
        query_serializer=QueryBackupLogSerializer(),
        responses={status.HTTP_200_OK: QueryBackupLogResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=QueryBackupLogSerializer)
    def query_clusters_backup_log(self, requests, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=BACKUP_LOG_RANGE_DAYS)
        backup_logs = MongoDBRestoreHandler.query_clusters_backup_log(**data, start_time=start_time, end_time=end_time)
        return Response(backup_logs)

    @common_swagger_auto_schema(
        operation_summary=_("查询定点构造记录"),
        query_serializer=QueryRestoreRecordSerializer(),
        responses={status.HTTP_200_OK: QueryRestoreRecordResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=QueryRestoreRecordSerializer, pagination_class=None)
    def query_restore_record(self, requests, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        filters = self.get_serializer().get_conditions(data)
        restore_records = MongoDBRestoreHandler.query_restore_record(
            kwargs["bk_biz_id"], data["limit"], data["offset"], filters
        )
        return Response(restore_records)
