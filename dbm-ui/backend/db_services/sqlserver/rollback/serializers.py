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
import json

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_services.sqlserver.cluster.serializers import GetDBForDrsSerializer
from backend.db_services.sqlserver.rollback import mock_data
from backend.ticket.builders.common.field import DBTimezoneField
from backend.utils.time import str2datetime


class QueryBackupLogsSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    days = serializers.IntegerField(help_text=_("查询时间间隔"), default=7, required=False)


class QueryBackupLogsResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.BACKUP_LOGS_DATA}


class QueryLatestBackupLogSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    rollback_time = DBTimezoneField(help_text=_("结束时间"))


class QueryLatestBackupLogResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.BACKUP_LOGS_DATA[0]}


class QueryDbsByBackupLogSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    db_pattern = serializers.ListSerializer(help_text=_("库匹配模式"), child=serializers.CharField())
    ignore_db = serializers.ListSerializer(help_text=_("忽略库匹配模式"), child=serializers.CharField())
    backup_logs = serializers.ListSerializer(help_text=_("备份记录"), child=serializers.JSONField(), required=False)
    restore_time = DBTimezoneField(help_text=_("回档时间"), required=False)

    def validate(self, attrs):
        if not attrs.get("backup_logs") and not attrs.get("rollback_time"):
            raise serializers.ValidationError(_("请输入备份记录或者备份时间来查询操作库表"))
        if attrs.get("restore_time"):
            attrs["restore_time"] = str2datetime(attrs["restore_time"])
        return attrs


class QueryDbsByBackupLogResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": ["test1", "test2", "test3"]}


class ImportDBStructByBackupSerializer(GetDBForDrsSerializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    db_excel = serializers.FileField(help_text=_("构造DB的excel文件"))
    db_list = serializers.CharField(help_text=_("db列表(逗号分隔)"))
    ignore_db_list = serializers.CharField(help_text=_("忽略db列表(逗号分割)"))

    backup_logs = serializers.CharField(help_text=_("备份记录(json转义)"), required=False)
    restore_time = DBTimezoneField(help_text=_("回档时间"), required=False)

    def validate(self, attrs):
        if not attrs.get("backup_logs") and not attrs.get("restore_time"):
            raise serializers.ValidationError(_("请保证输入回档信息"))

        attrs["backup_logs"] = json.loads(attrs["backup_logs"]) if attrs.get("backup_logs") else None
        attrs["restore_time"] = str2datetime(attrs["restore_time"]) if attrs.get("restore_time") else None
        attrs["db_list"] = attrs["db_list"].split(",")
        attrs["ignore_db_list"] = attrs["ignore_db_list"].split(",")
        return attrs


class ImportDBStructByBackupResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": [{"db_name": "a", "target_db_name": "b", "rename_db_name": "c"}]}
