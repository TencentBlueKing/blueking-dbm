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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.models import DBAdministrator
from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskStatus
from backend.db_report import mock_data
from backend.env import BK_SAAS_HOST, MYSQL_BACKUPRECOVER_BIZ_ID


class ReportCommonFieldSerializerMixin(serializers.Serializer):
    """巡检报告通用字段serializer类"""

    dba = serializers.SerializerMethodField(help_text=_("第一BDA"))

    def get_dba_map(self, db_type):
        if hasattr(self, "_dba_map"):
            return self._dba_map
        self._dba_map = {
            dba["bk_biz_id"]: dba["users"][0]
            for dba in DBAdministrator.objects.filter(db_type=db_type).values("bk_biz_id", "users")
        }
        return self._dba_map

    def get_dba(self, obj):
        return self.get_dba_map(self.context["view"].db_type).get(obj.bk_biz_id, "")


class GetReportOverviewSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.REPORT_OVERVIEW_DATA}


class GetReportCountSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.REPORT_COUNT_DATA}


class MySQLBackupRecoverTaskSerializer(serializers.ModelSerializer):
    """MySQL备份恢复任务序列化器"""

    recover_duration = serializers.SerializerMethodField(help_text=_("恢复花费时间(分钟)"))
    status = serializers.SerializerMethodField(help_text=_("任务状态(布尔值)"))
    task_id = serializers.SerializerMethodField(help_text=_("任务ID链接"))

    def get_recover_duration(self, obj):
        """计算恢复花费时间"""
        if obj.recover_start_time and obj.recover_end_time:
            duration = obj.recover_end_time - obj.recover_start_time
            return int(duration.total_seconds() / 60)  # 转换为分钟
        return None

    def get_status(self, obj):
        """将任务状态转换为布尔值"""
        # resource_return_success 和 recover_success 返回 True，其他状态返回 False
        return obj.task_status in [TaskStatus.RESOURCE_RETURN_SUCCESS, TaskStatus.RECOVER_SUCCESS]

    def get_task_id(self, obj):
        """生成任务ID的超链接"""
        if obj.task_id:
            # 从请求中获取业务ID，如果没有则使用模型中的业务ID
            # 超过120字符，拆分字符串避免检查不过
            return (
                f"{BK_SAAS_HOST}/{MYSQL_BACKUPRECOVER_BIZ_ID}/task-history/detail/{obj.task_id}?from=taskHistoryList"
            )
        return None

    class Meta:
        model = MySQLBackupRecoverTask
        fields = (
            "bk_biz_id",
            "cluster_domain",
            "backup_begin_time",
            "recover_duration",
            "status",
            "task_id",
            "charset",
            "mysql_version",
            "backup_type",
            "backup_tool",
            "create_at",
        )
        swagger_schema_fields = {"example": mock_data.REPORT_BACKUP_RECOVER_DATA}
