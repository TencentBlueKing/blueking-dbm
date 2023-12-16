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
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mongodb.restore.constants import BACKUP_LOG_RANGE_DAYS
from backend.db_services.mongodb.restore.handlers import MongoDBRestoreHandler
from backend.db_services.mongodb.restore.serializers import BackupLogRollbackTimeSerializer
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission

SWAGGER_TAG = "db_services/mongodb/restore"


class MongoDBRestoreViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("通过日志平台获取集群单据备份记录"),
        query_serializer=BackupLogRollbackTimeSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=BackupLogRollbackTimeSerializer)
    def query_ticket_backup_log(self, requests, *args, **kwargs):
        cluster_id = self.params_validate(self.get_serializer_class())["cluster_id"]
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=BACKUP_LOG_RANGE_DAYS)
        backup_logs = MongoDBRestoreHandler(cluster_id).query_ticket_backup_log(start_time, end_time)
        return Response(backup_logs)
