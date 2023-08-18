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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_services.mysql.fixpoint_rollback.constants import BACKUP_LOG_RANGE_DAYS

from . import mock_data


class BackupLogSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    days = serializers.IntegerField(help_text=_("查询时间间隔"), default=BACKUP_LOG_RANGE_DAYS, required=False)


class BackupLogRollbackTimeSerialzier(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    rollback_time = serializers.DateTimeField(help_text=_("回档时间"))
    job_instance_id = serializers.IntegerField(help_text=_("JOB实例ID"), required=False)


class QueryBackupLogJobSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    job_instance_id = serializers.IntegerField(help_text=_("JOB实例ID"))


class QueryFixpointLogSerializer(serializers.Serializer):
    limit = serializers.IntegerField(help_text=_("分页限制"), required=False, default=10)
    offset = serializers.IntegerField(help_text=_("分页起始"), required=False, default=0)


class QueryFixpointLogResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.FIXPOINT_LOG_DATA}
