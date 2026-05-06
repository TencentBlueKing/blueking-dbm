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

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskStatus
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_default
from backend.dbm_aiagent.mcp_tools.common.impl.taskflow_error_log import get_taskflow_error_logs
from backend.dbm_aiagent.mcp_tools.common.serializers.taskflow_log_query import (
    FailedTaskflowListInputSerializer,
    FailedTaskflowListOutputSerializer,
    TaskflowErrorLogOutputSerializer,
    TaskflowLogQueryInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.flow.consts import StateType
from backend.flow.models import FlowTree
from backend.iam_app.handlers.drf_perm.mcp import McpSkipPermission
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class TaskflowQueryMcpToolsViewSet(McpToolsViewSet):
    @mcp_tools_api_decorator(
        description=str(_("根据任务 root_id 查询最后一个失败节点的错误日志")),
        request_slz=TaskflowLogQueryInputSerializer,
        response_slz=TaskflowErrorLogOutputSerializer,
        tags=[DBMMCPTags.READ],
        permission_classes=[McpSkipPermission],
        mcp_auth_parser=auth_default,
        mcp=[DBMMcpTools.TASKFLOW_QUERY],
        name_prefix="taskflow_query",
    )
    def get_taskflow_error_logs(self, request, *args, **kwargs):
        root_id = self.get_param("root_id")
        result = get_taskflow_error_logs(root_id)
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(_("根据日期范围和单据类型查询失败的任务流 root_id 列表")),
        request_slz=FailedTaskflowListInputSerializer,
        response_slz=FailedTaskflowListOutputSerializer,
        tags=[DBMMCPTags.READ],
        permission_classes=[McpSkipPermission],
        mcp_auth_parser=auth_default,
        mcp=[DBMMcpTools.TASKFLOW_QUERY],
        name_prefix="taskflow_query",
    )
    def list_failed_taskflow(self, request, *args, **kwargs):
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        ticket_types = self.get_param("ticket_types")

        root_ids = []

        has_exercise = ticket_types and TicketType.MYSQL_ROLLBACK_EXERCISE.value in ticket_types
        other_types = (
            [t for t in ticket_types if t != TicketType.MYSQL_ROLLBACK_EXERCISE.value] if ticket_types else []
        )

        if has_exercise:
            exercise_root_ids = list(
                MySQLBackupRecoverTask.objects.filter(
                    create_at__gte=start_time,
                    create_at__lte=end_time,
                    task_status__in=[TaskStatus.RECOVER_FAILED, TaskStatus.COMMIT_FAILED],
                )
                .exclude(task_id="")
                .values_list("task_id", flat=True)
            )
            root_ids.extend(exercise_root_ids)

        # 当 ticket_types 为空（查全部）或存在非 MYSQL_ROLLBACK_EXERCISE 的类型时，查询 FlowTree
        if not ticket_types or other_types:
            qs = FlowTree.objects.filter(
                status=StateType.FAILED,
                created_at__gte=start_time,
                created_at__lte=end_time,
            )
            if ticket_types:
                # 排除 MYSQL_ROLLBACK_EXERCISE，避免与上方查询重复
                qs = qs.filter(ticket_type__in=other_types)
            else:
                # 查全部时，排除 MYSQL_ROLLBACK_EXERCISE（已通过 MySQLBackupRecoverTask 查询）
                qs = qs.exclude(ticket_type=TicketType.MYSQL_ROLLBACK_EXERCISE.value)
            root_ids.extend(qs.values_list("root_id", flat=True))

        return Response({"root_ids": list(set(root_ids))})
