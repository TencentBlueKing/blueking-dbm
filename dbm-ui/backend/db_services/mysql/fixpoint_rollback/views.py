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

from django.utils.translation import ugettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.db_services.mysql.fixpoint_rollback.serializers import (
    BackupLogRollbackTimeSerialzier,
    BackupLogSerializer,
    QueryBackupLogJobSerializer,
)
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission
from backend.utils.time import datetime2str

SWAGGER_TAG = "db_services/fixpoint_rollback"


class FixPointRollbackViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("通过日志平台获取集群备份记录"),
        query_serializer=BackupLogSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=BackupLogSerializer)
    def query_backup_log_from_bklog(self, requests, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        end_time = datetime.now()
        start_time = end_time - timedelta(days=validated_data["days"])
        logs = FixPointRollbackHandler(validated_data["cluster_id"]).query_backup_log_from_bklog(
            start_time=datetime2str(start_time), end_time=datetime2str(end_time)
        )
        return Response(logs)

    @common_swagger_auto_schema(
        operation_summary=_("通过下发脚本到机器获取集群备份记录"),
        query_serializer=BackupLogSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=BackupLogSerializer)
    def execute_backup_log_script(self, requests, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        logs = FixPointRollbackHandler(validated_data["cluster_id"]).execute_backup_log_script()
        return Response(logs)

    @common_swagger_auto_schema(
        operation_summary=_("根据job id查询任务执行状态和执行结果"),
        query_serializer=QueryBackupLogJobSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=QueryBackupLogJobSerializer)
    def query_backup_log_job(self, requests, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        resp = FixPointRollbackHandler(validated_data["cluster_id"]).query_backup_log_from_job(
            job_instance_id=validated_data["job_instance_id"]
        )
        return Response(resp)

    @common_swagger_auto_schema(
        operation_summary=_("查询小于回档时间点最近的备份记录"),
        query_serializer=BackupLogRollbackTimeSerialzier(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=BackupLogRollbackTimeSerialzier)
    def query_latest_backup_log(self, requests, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(
            FixPointRollbackHandler(validated_data["cluster_id"]).query_latest_backup_log(
                rollback_time=validated_data["rollback_time"],
                job_instance_id=validated_data.get("job_instance_id", None),
            )
        )
