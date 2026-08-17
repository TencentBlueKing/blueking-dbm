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

import logging
from functools import cached_property

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_report.enums import DrillFilterType, RedisRollbackExerciseTaskStage, ReportFieldFormat
from backend.db_report.models import RedisRollbackExerciseReport
from backend.db_report.register import register_drill_report
from backend.db_report.serializers import ReportCommonFieldSerializerMixin
from backend.db_report.views.revover_drill_report_view import RecoverDrillTaskViewSet
from backend.db_services.redis.rollback.config import RedisRollbackExerciseConfig
from backend.env import BK_SAAS_HOST

logger = logging.getLogger("root")


class RedisRecoverDrillTaskSerializer(serializers.ModelSerializer, ReportCommonFieldSerializerMixin):
    """Redis recover drill task serializer"""

    instance = serializers.SerializerMethodField(help_text=_("实例"))
    recover_duration = serializers.SerializerMethodField(help_text=_("恢复花费时间(分钟)"))
    rollback_flow_link = serializers.SerializerMethodField(help_text=_("构造流程链接"))
    delete_flow_link = serializers.SerializerMethodField(help_text=_("销毁流程链接"))
    ticket_link = serializers.SerializerMethodField(help_text=_("单据链接"))

    def get_instance(self, obj):
        """Combine ip:port as instance"""
        if obj.instance_ip and obj.instance_port:
            return f"{obj.instance_ip}:{obj.instance_port}"
        return ""

    def get_recover_duration(self, obj):
        """Calculate recovery duration in minutes"""
        if obj.recover_start_time and obj.recover_end_time:
            duration = obj.recover_end_time - obj.recover_start_time
            return round(duration.total_seconds() / 60, 2)
        return None

    @cached_property
    def rollback_exercise_bk_biz_id(self):
        """Load once per serializer; rollback/delete flows live in the exercise ticket biz."""
        return RedisRollbackExerciseConfig.from_settings().bk_biz_id

    def get_rollback_exercise_flow_biz_id(self, obj):
        """Use configured exercise biz for child flows, fallback to report biz if unset."""
        return self.rollback_exercise_bk_biz_id or obj.bk_biz_id

    def get_rollback_flow_link(self, obj):
        """Generate rollback flow link"""
        bk_biz_id = self.get_rollback_exercise_flow_biz_id(obj)
        if not obj.rollback_flow_obj_id or not bk_biz_id:
            return None
        return f"{BK_SAAS_HOST}/{bk_biz_id}/task-history/detail/{obj.rollback_flow_obj_id}?from=taskHistoryList"

    def get_delete_flow_link(self, obj):
        """Generate delete flow link"""
        bk_biz_id = self.get_rollback_exercise_flow_biz_id(obj)
        if not obj.delete_flow_obj_id or not bk_biz_id:
            return None
        return f"{BK_SAAS_HOST}/{bk_biz_id}/task-history/detail/{obj.delete_flow_obj_id}?from=taskHistoryList"

    def get_ticket_link(self, obj):
        """Generate ticket link"""
        if not obj.ticket_id or not obj.bk_biz_id:
            return None
        return f"{BK_SAAS_HOST}/ticket/{obj.ticket_id}"

    class Meta:
        model = RedisRollbackExerciseReport
        fields = (
            "bk_biz_id",
            "dba",
            "cluster_domain",
            "cluster_type",
            "instance",
            "redis_version",
            "recover_start_time",
            "recover_duration",
            "state",
            "ticket_link",
            "rollback_flow_link",
            "delete_flow_link",
            "task_message",
            "backup_info",
        )


@register_drill_report(DBType.Redis)
class RedisRecoverDrillTaskViewSet(RecoverDrillTaskViewSet):
    """Redis recover drill task viewset"""

    queryset = RedisRollbackExerciseReport.objects.filter(
        task_stage__in=[
            RedisRollbackExerciseTaskStage.DONE,
            RedisRollbackExerciseTaskStage.TICKET_GEN_FAILED,
            RedisRollbackExerciseTaskStage.RESOURCE_APPLI_FAILED,
            RedisRollbackExerciseTaskStage.ROLLBACK_FAILED,
            RedisRollbackExerciseTaskStage.CLEANUP_FAILED,
            RedisRollbackExerciseTaskStage.SCENE_PRESERVED,
            RedisRollbackExerciseTaskStage.SKIPPED,
            RedisRollbackExerciseTaskStage.BACKUP_INVALID,
        ]
    ).order_by("-update_at")
    serializer_class = RedisRecoverDrillTaskSerializer

    filter_fields = {
        "bk_biz_id": ["exact", "in"],
        "cluster_domain": ["exact", "in"],
        "cluster_type": ["exact", "in"],
        "task_stage": ["exact", "in"],
        "state": ["exact", "in"],
        "create_at": ["gte", "lte"],
    }
    ordering_fields = ["recover_start_time"]

    report_title = [
        {
            "name": "bk_biz_id",
            "display_name": _("业务"),
            "format": ReportFieldFormat.TEXT.value,
            "filter": {"type": DrillFilterType.BIZ},
        },
        {
            "name": "dba",
            "display_name": _("DBA"),
            "format": ReportFieldFormat.TEXT.value,
            "filter": {"type": DrillFilterType.TEXT},
        },
        {
            "name": "cluster_domain",
            "display_name": _("域名"),
            "format": ReportFieldFormat.TEXT.value,
            "filter": {"type": DrillFilterType.TEXT},
        },
        {
            "name": "cluster_type",
            "display_name": _("架构类型"),
            "format": ReportFieldFormat.TEXT.value,
            "filter": {"type": DrillFilterType.TEXT},
        },
        {
            "name": "instance",
            "display_name": _("实例"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "redis_version",
            "display_name": _("Redis版本"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "recover_start_time",
            "display_name": _("回档开始时间"),
            "format": ReportFieldFormat.TIME.value,
            "ordering": True,
        },
        {
            "name": "recover_duration",
            "display_name": _("恢复花费时间(分钟)"),
            "format": ReportFieldFormat.TEXT.value,
        },
        {
            "name": "state",
            "display_name": _("状态"),
            "format": ReportFieldFormat.STATUS.value,
        },
        {
            "name": "ticket_link",
            "display_name": _("单据链接"),
            "format": ReportFieldFormat.LINK.value,
        },
        {
            "name": "rollback_flow_link",
            "display_name": _("构造流程链接"),
            "format": ReportFieldFormat.LINK.value,
        },
        {
            "name": "delete_flow_link",
            "display_name": _("销毁流程链接"),
            "format": ReportFieldFormat.LINK.value,
        },
        {
            "name": "task_message",
            "display_name": _("任务日志"),
            "format": ReportFieldFormat.LOG.value,
        },
        {
            "name": "backup_info",
            "display_name": _("备份信息"),
            "format": ReportFieldFormat.LOG.value,
        },
    ]
