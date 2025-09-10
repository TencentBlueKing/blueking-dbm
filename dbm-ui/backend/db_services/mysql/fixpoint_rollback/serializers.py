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
from backend.ticket.builders.common.constants import MySQLBackupSource, MySQLBackupType
from backend.ticket.builders.common.field import DBTimezoneField
from backend.utils.time import str2datetime

from . import mock_data


class BackupLogSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    days = serializers.IntegerField(help_text=_("查询时间间隔"), default=BACKUP_LOG_RANGE_DAYS, required=False)
    backup_method = serializers.ChoiceField(
        help_text=_("备份类型"),
        choices=MySQLBackupType.get_choices(),
        required=False,
        default="default",
    )


class BackupLogTendbResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.TENDBCLUSTER_BACKUP_LOG_FROM_BKLOG}


class BackupLogMySQLResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.MYSQL_BACKUP_LOG_FROM_BKLOG}


class BackupLocalLogMySQLResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.MYSQL_BACKUP_LOG_FROM_BKLOG}


class BackupLogRollbackTimeSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    rollback_time = DBTimezoneField(help_text=_("回档时间"))
    backup_source = serializers.ChoiceField(
        help_text=_("备份源"), choices=MySQLBackupSource.get_choices(), required=False, default=MySQLBackupSource.REMOTE
    )
    backup_method = serializers.ChoiceField(
        help_text=_("备份类型"),
        choices=MySQLBackupType.get_choices(),
        required=False,
        default="default",
    )


class FilterBackupLogSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    deadlines_days = serializers.IntegerField(help_text=_("指定备份天数前数据"), required=False)
    latest_time = serializers.DateTimeField(help_text=_("备份最迟的时间"), required=False)
    backup_method = serializers.ChoiceField(
        help_text=_("过滤备份类型"),
        choices=MySQLBackupType.get_choices(),
        required=False,
    )
    is_full_backup = serializers.BooleanField(help_text=_("是否为全备"), required=False, default=False)
    backup_source = serializers.ChoiceField(
        help_text=_("备份源"), choices=MySQLBackupSource.get_choices(), required=False, default=MySQLBackupSource.REMOTE
    )

    def validate(self, data):
        # 为备份方法提供默认值并将其转换为列表
        default_backup_methods = "full_by_ticket,full_by_regular,partial_by_ticket"
        backup_method = data.get("backup_method", default_backup_methods)
        data["backup_method"] = backup_method.split(",")

        # 处理 last_time 字段并将其转换为 datetime 对象
        latest_time = data.get("latest_time")
        data["latest_time"] = str2datetime(latest_time) if latest_time else None

        return data


class BackupLogRollbackTimeTendbResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.TENDBCLUSTER_BACKUP_LOG_FROM_BKLOG[0]}


class BackupLogRollbackTimeMySQLResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.MYSQL_BACKUP_LOG_FROM_BKLOG[0]}


class QueryBackupLogJobSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    job_instance_id = serializers.IntegerField(help_text=_("JOB实例ID"))


class QueryFixpointLogSerializer(serializers.Serializer):
    limit = serializers.IntegerField(help_text=_("分页限制"), required=False, default=10)
    offset = serializers.IntegerField(help_text=_("分页起始"), required=False, default=0)


class QueryFixpointLogResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.FIXPOINT_LOG_DATA}
